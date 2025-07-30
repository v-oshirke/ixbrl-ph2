import { Container, Typography, Button, Box, Grid } from '@mui/material';
import BlobList, { SelectedBlob, DateRefType } from './components/BlobList';
import { useState, useRef, useEffect } from 'react';

type UserInfo = {
  userDetails?: string;
  userId?: string;
  [key: string]: any;
};

function App() {
  const [selectedBlobs, setSelectedBlobs] = useState<SelectedBlob[]>([]);
  const dateRef = useRef<DateRefType>(null); // ✅ ref to access dates
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);

  useEffect(() => {
    fetch('/auth/me')
      .then(res => res.json())
      .then(data => setUserInfo(data))
      .catch(() => setUserInfo(null));
  }, []);

  // Azure Function URLs
  const azureFunctionUrls = {
    processUploads: '/api/processUploads',
    callAoai: '/api/callAoai'
  };

  // Generic function to call Azure Functions
  const callAzureFunction = async (url: string, requiredContainer: string) => {
    const validBlobs = selectedBlobs.filter(blob => blob.container === requiredContainer);
    if (validBlobs.length === 0) {
      alert(`Please select a file in the ${requiredContainer} container for this function to process`);
      return;
    }

    // Check: Ensure that no files outside the required container are selected
    if (selectedBlobs.some(blob => blob.container !== requiredContainer)) {
      alert(`Please select only files in the ${requiredContainer} container for this function to process`);
      return;
    }

    // ✅ Get selected dates from BlobList via ref
    const selectedDates = dateRef.current?.getSelectedDates() ?? {};

    console.log("🟢 Selected Dates from ref:", selectedDates);
    console.log("🟢 Selected Blobs:", selectedBlobs);

    const payload = {
      blobs: selectedBlobs,
      selectedDates
    };

    console.log("📦 Final Payload Being Sent:", payload);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const contentType = response.headers.get("content-type");

      let data;
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        const responseText = await response.text();
        console.error("Unexpected response format:", responseText);
        throw new Error(`Unexpected response format: ${responseText}`);
      }

      if (!response.ok) {
        console.error('Azure Function response:', data);
        alert(`Error: ${data.errors?.join('\n') || 'Unknown error'}`);
      } else {
        console.log('Azure Function response:', data);
        alert(`Azure Function completed successfully! Processed files: ${data.processedFiles?.join(', ')}`);
      }
    } catch (error) {
      console.error('Error calling Azure Function:', error);
      alert(`Error: ${error}`);
    }
  };

  return (
    <Container maxWidth={false} disableGutters sx={{ textAlign: 'center', py: 0 }}>
      <Box
        sx={{
          backgroundColor: '#0A1F44',
          color: 'white',
          py: 3,
          px: 2,
          textAlign: 'center',
          boxShadow: 3,
        }}
      >
        <Typography variant="h4" gutterBottom>
          EY IXBRL DOCUMENT REVIEWER
        </Typography>
        {userInfo && (
          <Typography variant="body2" sx={{ color: 'white', mb: 1 }}>
            Signed in as: {userInfo.userDetails ?? ''} {userInfo.userId ? `(${userInfo.userId})` : ''}
          </Typography>
        )}
        <Box display="flex" justifyContent="center" gap={2} marginTop={2}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => callAzureFunction(azureFunctionUrls.processUploads, "bronze")}
            style={{ display: 'none' }}
          >
            Extract Text
          </Button>
          <Button
            variant="contained"
            color="secondary"
            onClick={() => callAzureFunction(azureFunctionUrls.callAoai, "silver")}
          >
            Call AOAI
          </Button>
        </Box>
      </Box>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <BlobList
            onSelectionChange={setSelectedBlobs}
            ref={dateRef} // ✅ Pass date ref to BlobList
          />
        </Grid>
      </Grid>
    </Container>
  );
}

export default App;