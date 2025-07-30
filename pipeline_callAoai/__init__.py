from concurrent.futures import ThreadPoolExecutor, as_completed
import azure.functions as func
import logging
import json
import io
import os
import pandas as pd
from utils.prompts import load_prompts
from utils.blob_functions import get_blob_content, write_to_blob, list_blobs
from utils.azure_openai import run_prompt
from bs4 import BeautifulSoup
from datetime import datetime, timezone
 
# Define batch size (adjust based on LLM token limits)
BATCH_SIZE = 10

def process_blob(blob):
    """Extract relevant Excel content for LLM validation."""
    blob_name = blob.get("name")
    container_name = blob.get("container", "silver")
    # result = {"blob_name": blob_name, "excel_rows": [], "error": None}
    # result = {"blob_name": blob_name, "excel_rows": [], "taxonomy_data": None, "error": None}
    result = {"blob_name": blob_name, "excel_rows": [], "taxonomy_data": [],"unique_periods": [],"statement_of_compliance_text": None, "error": None}
 
 
    if not blob_name:
        result["error"] = "Blob missing 'name'"
        return result
 
    if container_name == "bronze":
        result["error"] = f"Blobs from 'bronze' container not allowed: {blob_name}"
        return result
 
    try:
        blob_bytes = get_blob_content(container_name, blob_name)
        ext = os.path.splitext(blob_name)[1].lower()
 
        if ext in ['.xlsx', '.xls']:
            xls = pd.ExcelFile(io.BytesIO(blob_bytes))
            # df = pd.read_excel(xls, sheet_name='Filing Details')
 
            # # Extract required columns
            # df = df[['Line Item Description', 'Concept Label', 'Comment Text']].dropna(how='all')
            df_filing_details = pd.read_excel(xls, sheet_name='Filing Details')
 
            # Extract relevant columns for LLM validation
            df = df_filing_details[['Line Item Description', 'Concept Label', 'Comment Text','Dimensions']].dropna(how='all')
 
            # Extract unique 'Period' values
            if 'Period' in df_filing_details.columns:
                unique_periods = df_filing_details['Period'].dropna().unique().tolist()
                logging.info(f"[{blob_name}] Extracted Periods from Excel: {unique_periods}")

            else:
                unique_periods = []
                logging.info(f"[{blob_name}] Extracted Periods from Excel: {unique_periods}")
 
            result["excel_rows"] = df.to_dict(orient='records')
            result["unique_periods"] = unique_periods
 
            # taxonomy_df = pd.read_excel(xls, sheet_name='Filing Information')
            # result["taxonomy_data"] = taxonomy_df.to_dict(orient='records')
            if 'Filing Information' in xls.sheet_names:
                taxonomy_df = pd.read_excel(xls, sheet_name='Filing Information')
                if not taxonomy_df.empty:
                    result["taxonomy_data"] = taxonomy_df.to_dict(orient='records')
                else:
                    logging.warning(f"'Filing Information' sheet is empty in blob {blob_name}")
            else:
                logging.warning(f"'Filing Information' sheet missing in blob {blob_name}")
       
        elif ext == '.html':
            try:
                soup = BeautifulSoup(blob_bytes.decode('utf-8', errors='ignore'), 'html.parser')
 
                start_tag = None
                for p in soup.find_all("p"):
                    if "STATEMENT OF COMPLIANCE" in p.get_text(strip=True).upper():
                        start_tag = p
                        break
 
                content = []
                if start_tag:
                    current = start_tag
                    while current:
                        text = current.get_text(strip=True)
                        if text.startswith("2.") and "ACCOUNTING POLICIES" in text.upper():
                            break
                        if text:
                            content.append(text)
                        current = current.find_next_sibling("p")
 
                result["statement_of_compliance_text"] = "\n".join(content)
 
            except Exception as e:
                result["error"] = f"Error extracting HTML content from {blob_name}: {str(e)}"
 
    except Exception as e:
        result["error"] = f"Error processing blob {blob_name}: {str(e)}"
 
    return result
 
def batch_rows(rows, batch_size):
    """Split rows into smaller batches."""
    for i in range(0, len(rows), batch_size):
        yield rows[i:i + batch_size]
 
def validate_with_llm(rows):
    """Send batches of rows to LLM for validation."""
    validated_rows = []
    prompts = load_prompts()  
    system_prompt = prompts["system_prompt"]
    user_prompt_template = prompts["user_prompt"]  
 
    for batch in batch_rows(rows, BATCH_SIZE):
        # Use the user prompt from backend instead of constructing it manually
        user_prompt = user_prompt_template.format(data=json.dumps(batch, indent=2))
 
        response = run_prompt(system_prompt, user_prompt)
        try:
            response = response.strip()
 
            # Handle Markdown formatting from LLM like ```json ... ```
            if response.startswith("```json"):
                response = response.strip("`").replace("json", "", 1).strip()
            elif response.startswith("```"):
                response = response.strip("`").strip()
 
            # Ensure it's still a string before proceeding
            if not isinstance(response, str):
                logging.error("LLM response is not a valid string.")
                validated_rows.append({"error": "Invalid LLM response type"})
                continue
 
            if not response.startswith("[") and not response.startswith("{"):
                logging.error("LLM response is not valid JSON format")
                validated_rows.append({"error": "Invalid JSON format from LLM"})
                continue
 
            parsed_response = json.loads(response)
 
            # Optional: skip if it's [{}] or [{}] * n
            if isinstance(parsed_response, list) and all(isinstance(item, dict) and not item for item in parsed_response):
                logging.warning("Skipping empty [{}] response from LLM")
                continue
            logging.info(f'ROW BY ROW VALIDATION --> : {parsed_response}')
            validated_rows.extend(parsed_response)
 
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {str(e)}")
            validated_rows.append({"error": f"Invalid JSON format from LLM: {str(e)}"})
 
    return validated_rows
 
def validate_taxonomy_with_llm(taxonomy_data):
    prompts = load_prompts()
    system_prompt = prompts.get("system_prompt_taxonomy", "")  # Use separate system prompt
    taxonomy_prompt = prompts["taxonomy"]
 
    try:
        logging.info(f"YE HAI TAXANOMY DATA:  {taxonomy_data}")

        user_prompt = taxonomy_prompt.format(data=json.dumps(taxonomy_data, indent=2))
        response = run_prompt(system_prompt, user_prompt).strip()
        logging.info(f'TAXANOMY:{response}')
 
        # Clean LLM formatting
        if response.startswith("```json"):
            response = response.strip("`").replace("json", "", 1).strip()
        elif response.startswith("```"):
            response = response.strip("`").strip()
 
        if not response.startswith("[") and not response.startswith("{"):
            logging.error("LLM taxonomy response is not valid JSON format")
            return [{"error": "Invalid taxonomy response format from LLM"}]
 
        return json.loads(response)
 
    except Exception as e:
        logging.error(f"Taxonomy LLM processing error: {str(e)}")
        return [{"error": f"Taxonomy validation failed: {str(e)}"}]
 
def validate_periods_with_llm(unique_periods, input_dates):
    prompts = load_prompts()
    system_prompt = prompts.get("system_prompt_period_validation", "")
    user_prompt_template = prompts.get("user_prompt_period_validation", "")
 
    try:
        user_prompt = user_prompt_template.format(
            periods=json.dumps(unique_periods, indent=2),
            input_dates=json.dumps(input_dates, indent=2)
        )
 
        response = run_prompt(system_prompt, user_prompt).strip()
        logging.info(f'PERIOD VALIDATION LLM RESPONSE: {response}')
 
        # Clean LLM formatting
        if response.startswith("```json"):
            response = response.strip("`").replace("json", "", 1).strip()
        elif response.startswith("```"):
            response = response.strip("`").strip()
 
        if not response.startswith("[") and not response.startswith("{"):
            logging.error("LLM period validation response is not valid JSON format")
            return [{"error": "Invalid period validation response format from LLM"}]
 
        return json.loads(response)
 
    except Exception as e:
        logging.error(f"Period validation LLM processing error: {str(e)}")
        return [{"error": f"Period validation failed: {str(e)}"}]

def concept_label_filter(excel_rows, matched_taxonomy_blob_name):
    """Filter excel rows based on concept label match with taxonomy file."""
    try:
        taxonomy_bytes = get_blob_content("taxanomy", matched_taxonomy_blob_name)
        xls = pd.ExcelFile(io.BytesIO(taxonomy_bytes))

        if "Presentation" not in xls.sheet_names:
            logging.warning(f"'Presentation' sheet not found in {matched_taxonomy_blob_name}")
            return excel_rows, []

        presentation_df = pd.read_excel(xls, sheet_name="Presentation")
        if "Label" not in presentation_df.columns:
            logging.warning(f"'Label' column not found in Presentation sheet of {matched_taxonomy_blob_name}")
            return excel_rows, []

        labels_set = set(presentation_df["Label"].dropna().astype(str).str.strip())

        matched_rows = []
        unmatched_rows = []

        for row in excel_rows:
            concept = str(row.get("Concept Label", "")).strip()
            # logging.info(f"Checking CONCEPT LABEL FROM SILVER '{concept}'")

            if concept in labels_set:
                matched_rows.append(row)
            else:
                unmatched_rows.append(row)


        logging.info(f"✅ {len(matched_rows)} rows matched from {matched_taxonomy_blob_name}")
        # logging.info(f"{matched_rows} : MATCHED LABEL")

        logging.warning(f"⚠️ {len(unmatched_rows)} rows did not match in Presentation sheet")
        # logging.warning(f"⚠️ {unmatched_rows} : UNMATCHED LABEL")

        return matched_rows, unmatched_rows

    except Exception as e:
        logging.error(f"Failed concept_label_filter for {matched_taxonomy_blob_name}: {str(e)}")
        return excel_rows, []

 

def _main_logic(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # 🔍 List all taxonomy files in taxonomy container
    taxonomy_blobs = list_blobs("taxanomy")
    taxonomy_blobs_list = list(taxonomy_blobs)  # convert iterable to list for reuse
    logging.info("📁 Listing blobs in 'taxanomy' container:")
    for blob in taxonomy_blobs_list:
        logging.info(f"🗂️ {blob.name}")
 
    req_body = req.get_json()
    selected_blobs = req_body.get("blobs", None)
    input_dates = req_body.get("selectedDates", [])
 
    # input_dates = req_body.get("input_dates", [])  # Expecting UI to send dates here
    # input_dates = {
    # "end_date_current": "2023-12-31",
    # "duration_current": {
    #     "start": "2023-01-01",
    #     "end": "2023-12-31"
    # },
    # "end_date_prior": "2022-12-31",
    # "duration_prior": {
    #     "start": "2022-01-01",
    #     "end": "2022-12-31"
    # },
    # "opening_date_prior": "2021-12-31"
    # }

    if not selected_blobs:
        return func.HttpResponse(
            json.dumps({"error": "No blobs provided."}),
            status_code=400,
            mimetype="application/json"
        )
 
    errors = []
    validated_data = []
    taxonomy_data_to_validate = []
 
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_blob, blob) for blob in selected_blobs]

        blob_results = []
        all_periods = []


        for future in as_completed(futures):
            res = future.result()
            blob_results.append(res)

                # 🔍 Find the matching taxonomy file for this blob
            matched_taxonomy_file = None
            if res["taxonomy_data"]:
                for row in res["taxonomy_data"]:
                    taxonomy_name = row.get("Taxonomy") or row.get("Taxonomy Name") or row.get("Name")
                    if not taxonomy_name:
                        continue

                    lower = taxonomy_name.lower()
                    if "frs 101" in lower:
                        base = "frs101"
                    elif "frs 102" in lower:
                        base = "frs102"
                    elif "ifrs" in lower:
                        base = "ifrs"
                    else:
                        base = "unknown"

                    if "irish" in lower:
                        region = "irish"
                    elif "uk" in lower:
                        region = "uk"
                    else:
                        region = "unknown"

                    for blob in taxonomy_blobs_list:
                        file_name = blob.name.lower()
                        if region == "uk" and "ireland" not in file_name and base in file_name:
                            matched_taxonomy_file = blob.name
                            logging.info(f"✅ Matched taxonomy '{taxonomy_name}' → '{blob.name}'")
                            break
                        if region == "irish" and "ireland" in file_name and base in file_name:
                            matched_taxonomy_file = blob.name
                            logging.info(f"✅ Matched taxonomy '{taxonomy_name}' → '{blob.name}'")
                            break

                    if matched_taxonomy_file:
                        break

            res["matched_taxonomy_file"] = matched_taxonomy_file


            if res["error"]:
                errors.append(res["error"])
            all_periods.extend(res.get("unique_periods", []))

            # LLM input prep (leave as is)
            if res["taxonomy_data"]:
                taxonomy_data_to_validate.extend(res["taxonomy_data"])
            if res.get("statement_of_compliance_text"):
                taxonomy_data_to_validate.append({
                    "source": "html_statement_of_compliance",
                    "content": res["statement_of_compliance_text"]
                })
 
 
        # first: validate taxonomy first
        if taxonomy_data_to_validate:
            taxonomy_result = validate_taxonomy_with_llm(taxonomy_data_to_validate)
            validated_data.append({"taxonomy_validation": taxonomy_result})
        else:
            logging.warning("No taxonomy data found across all blobs.")
        # second : validate the dates
        if input_dates:
            period_validation_result = validate_periods_with_llm(all_periods, input_dates)
            validated_data.append({"period_validation": period_validation_result})
        else:
            logging.warning("No input dates provided for period validation.")
 
        # Third: now validate Excel rows after taxonomy is validated

        # for res in blob_results:
        #     if res["excel_rows"]:
        #         validated_data.extend(validate_with_llm(res["excel_rows"]))
        
        for res in blob_results:
            if res["excel_rows"]:
                matched_file = "FRC-2023-v1.0.1-FRS-101.xlsx"
                if matched_file:
                    filtered_rows, unmatched_rows = concept_label_filter(res["excel_rows"], matched_file)
                    logging.info(f"✅LLM KO MATCHED CONCEPT LABELS BHEJRE --> {len(filtered_rows)}")
                    validated_data.extend(validate_with_llm(filtered_rows))

                    # Optional: log or save unmatched rows
                    if unmatched_rows:
                        logging.warning(f"⚠️ {len(unmatched_rows)} unmatched Concept Labels in {res['blob_name']}")
                                        # Add unmatched concept labels with validation message
                        for row in unmatched_rows:
                            validated_data.append({
                                "Concept Label": row.get("Concept Label"),
                                "validation_errors": ["Stating the Concept Label is not present in the taxonomy"]
                            })

                else:
                    logging.warning(f"❌ No matched taxonomy file found for {res['blob_name']}. Sending all rows to LLM.")
                    # validated_data.extend(validate_with_llm(res["excel_rows"]))

 
 
    # Validate JSON
    try:
        json.dumps(validated_data)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON from LLM: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON format from LLM"}),
            status_code=500,
            mimetype="application/json"
        )
 
    # Save to blob
    # output_name = "validated-output.json"

# Use first blob name for output naming
    first_blob_name = selected_blobs[0]["name"]
    base_filename = os.path.splitext(os.path.basename(first_blob_name))[0]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    output_name = f"{base_filename}-validated-output-{timestamp}.json"

    write_to_blob("gold", output_name, json.dumps(validated_data, indent=2).encode('utf-8'))
 
    return func.HttpResponse(
        json.dumps({
            "processedFiles": [b["name"] for b in selected_blobs],
            "errors": errors,
            "outputFile": output_name,
            # "validated_data": validated_data,
            "status": "completed" if not errors else "completed_with_errors"
        }),
        status_code=200,
        mimetype="application/json"
    )

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return _main_logic(req)
    except Exception as e:
        logging.error(f"Fatal error in main: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
)