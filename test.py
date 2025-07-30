{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "48809fa3",
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "=== Token Header ===\n",
      "{\n",
      "    \"typ\": \"JWT\",\n",
      "    \"alg\": \"RS256\",\n",
      "    \"x5t\": \"JYhAcTPMZ_LX6DBlOWQ7Hn0NeXE\",\n",
      "    \"kid\": \"JYhAcTPMZ_LX6DBlOWQ7Hn0NeXE\"\n",
      "}\n",
      "\n",
      "=== Token Payload ===\n",
      "{\n",
      "    \"aud\": \"https://storage.azure.com\",\n",
      "    \"iss\": \"https://sts.windows.net/16b3c013-d300-468d-ac64-7eda0820b6d3/\",\n",
      "    \"iat\": 1753551911,\n",
      "    \"nbf\": 1753551911,\n",
      "    \"exp\": 1753557469,\n",
      "    \"acr\": \"1\",\n",
      "    \"aio\": \"AbQAS/8ZAAAAgB+yHtSo3RGKK6AFpQo/9CZl4HwPRcX+cIFahrrNQPD8FcoF7DpsH/B8eR23TfRdaT1jyCOJSq0C6z9yIn/gKjRf1Wt2lm6jNVQzEI//VJ3dvvzsiDbCM+Y0LorTutmYSoS6j5WzYl8Ocui9G5bj1nMl5wqIZVaMaN0FWPmvtJbBTVDlmMCTJ+wKytQjunU+VFzgIVRoPxurUJmRKuxelyGbeE7W05wQzKBRpEXXLm0=\",\n",
      "    \"altsecid\": \"5::100320041F2FB918\",\n",
      "    \"amr\": [\n",
      "        \"rsa\",\n",
      "        \"mfa\"\n",
      "    ],\n",
      "    \"appid\": \"04b07795-8ddb-461a-bbee-02f9e1bf7b46\",\n",
      "    \"appidacr\": \"0\",\n",
      "    \"deviceid\": \"660afd36-31f7-4441-b930-9daf99ed89e4\",\n",
      "    \"email\": \"v-oshirke@microsoft.com\",\n",
      "    \"family_name\": \"SHIRKE (International Supplier)\",\n",
      "    \"given_name\": \"OMKAR\",\n",
      "    \"groups\": [\n",
      "        \"e3096df7-b65c-4e32-ab1a-7a35dc684f0a\",\n",
      "        \"d34c4ebe-4984-4903-a64d-8c20283d516b\"\n",
      "    ],\n",
      "    \"idp\": \"https://sts.windows.net/72f988bf-86f1-41af-91ab-2d7cd011db47/\",\n",
      "    \"idtyp\": \"user\",\n",
      "    \"ipaddr\": \"2409:40c2:205a:bd4b:4081:5ac6:c336:fa10\",\n",
      "    \"name\": \"v-oshirke\",\n",
      "    \"oid\": \"9c0a7189-3473-4725-9d25-02f553f3255e\",\n",
      "    \"puid\": \"10032004DF6ED0FD\",\n",
      "    \"pwd_url\": \"https://portal.microsoftonline.com/ChangePassword.aspx\",\n",
      "    \"rh\": \"1.AUYAE8CzFgDTjUasZH7aCCC204GmBuTU86hCkLbCsClJevHxAK9GAA.\",\n",
      "    \"scp\": \"user_impersonation\",\n",
      "    \"sid\": \"006bc209-adde-346a-da88-3e249604d215\",\n",
      "    \"sub\": \"JpVZvYQhRLanN7JDb8QS9RpFz0EbAb8C8E7iuJdoEpI\",\n",
      "    \"tid\": \"16b3c013-d300-468d-ac64-7eda0820b6d3\",\n",
      "    \"unique_name\": \"v-oshirke@microsoft.com\",\n",
      "    \"uti\": \"TP-2EoshAEOHYf3DGlqIAA\",\n",
      "    \"ver\": \"1.0\",\n",
      "    \"xms_ftd\": \"Gi2wLtaib-TiXby2RPlGQCpzTuJMKlr8Ms-XUp0XhBcBdXNub3J0aC1kc21z\",\n",
      "    \"xms_idrel\": \"5 26\"\n",
      "}\n"
     ]
    },
    {
     "name": "stderr",
     "output_type": "stream",
     "text": [
      "WARNING:azure.identity._internal.decorators:AzureCliCredential.get_token_info failed: Please run 'az login' to set up an account\n",
      "WARNING:azure.identity._internal.decorators:AzureCliCredential.get_token_info failed: Please run 'az login' to set up an account\n"
     ]
    }
   ],
   "source": [
    "from utils.blob_functions import get_blob_content, list_blobs\n",
    "\n",
    "taxonomy_blobs = list_blobs(\"taxanomy\")\n",
    "for blob in taxonomy_blobs:\n",
    "    print(\"📄\", blob.name)  # List all available taxonomy Excel files\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "5d738c39",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.13.5"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
