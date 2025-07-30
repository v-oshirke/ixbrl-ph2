// Full updated BlobList.tsx with correct date auto-population logic

import React, {
  useEffect,
  useState,
  useImperativeHandle,
  forwardRef
} from 'react';
import {
  Button, Card, CardContent, Typography, Box, List, ListItem,
  ListItemText, Link, Checkbox, TextField, Grid, Alert
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import dayjs from 'dayjs';

const CONTAINER_NAMES = ['silver', 'gold'];
const CONTAINER_LABELS: Record<string, string> = {
  silver: 'Input',
  gold: 'Output',
};
const functionUrl = `/api/app_getBlobsByContainer`;

interface BlobItem {
  name: string;
  url: string;
}

export interface SelectedBlob extends BlobItem {
  container: string;
}

export interface DateRefType {
  getSelectedDates: () => {
    end_date_current: string;
    duration_current: { start: string; end: string };
    end_date_prior: string;
    duration_prior: { start: string; end: string };
    opening_date_prior: string;
  };
}

interface BlobListProps {
  onSelectionChange?: (selected: SelectedBlob[]) => void;
  dateRef?: React.Ref<DateRefType>;
}

const BlobList = forwardRef<DateRefType, BlobListProps>(({ onSelectionChange }, ref) => {
  const [blobsByContainer, setBlobsByContainer] = useState<Record<string, BlobItem[]>>({
    silver: [],
    gold: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedBlobs, setSelectedBlobs] = useState<SelectedBlob[]>([]);

  const [endCurrent, setEndCurrent] = useState('');
  const [startCurrent, setStartCurrent] = useState('');
  const [endPrior, setEndPrior] = useState('');
  const [startPrior, setStartPrior] = useState('');
  const [openPrior, setOpenPrior] = useState('');

  const [fieldsDisabled, setFieldsDisabled] = useState(true);
  const [showConfirmBox, setShowConfirmBox] = useState(false);

  useImperativeHandle(ref, () => {
    const dates = {
      end_date_current: endCurrent,
      duration_current: {
        start: startCurrent,
        end: endCurrent
      },
      end_date_prior: endPrior,
      duration_prior: {
        start: startPrior,
        end: endPrior
      },
      opening_date_prior: openPrior
    };

    return {
      getSelectedDates: () => dates
    };
  });

  const fetchBlobsFromAllContainers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(functionUrl);
      if (!response.ok) throw new Error(`Error: ${response.status} - ${response.statusText}`);
      const data: Record<string, BlobItem[]> = await response.json();
      setBlobsByContainer(data);
    } catch (err: any) {
      setError(`Error: ${err.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
      resetDates();
    }
  };

  const resetDates = () => {
    setEndCurrent('');
    setStartCurrent('');
    setEndPrior('');
    setStartPrior('');
    setOpenPrior('');
    setFieldsDisabled(true);
    setShowConfirmBox(false);
  };

  useEffect(() => {
    fetchBlobsFromAllContainers();
  }, []);

  const toggleSelection = (container: string, blob: BlobItem) => {
    const exists = selectedBlobs.some(b => b.name === blob.name && b.container === container);
    const newSelection = exists
      ? selectedBlobs.filter(b => !(b.name === blob.name && b.container === container))
      : [...selectedBlobs, { ...blob, container }];
    setSelectedBlobs(newSelection);
    onSelectionChange?.(newSelection);
  };

  const handleEndCurrentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedDate = e.target.value;
    setEndCurrent(selectedDate);
    const date = dayjs(selectedDate);

    const isDec31 = date.date() === 31 && date.month() === 11;
    const isMar31 = date.date() === 31 && date.month() === 2;

    if (isDec31) {
      const startCurrent = dayjs(`${date.year()}-01-01`);
      const startPrior = dayjs(`${date.year() - 1}-01-01`);
      const endPrior = dayjs(`${date.year() - 1}-12-31`);

      setStartCurrent(startCurrent.format('YYYY-MM-DD'));
      setStartPrior(startPrior.format('YYYY-MM-DD'));
      setEndPrior(endPrior.format('YYYY-MM-DD'));
      setOpenPrior(startPrior.format('YYYY-MM-DD'));
    } else if (isMar31) {
      const startCurrent = dayjs(`${date.year() - 1}-04-01`);
      const startPrior = dayjs(`${date.year() - 2}-04-01`);
      const endPrior = dayjs(`${date.year() - 1}-03-31`);

      setStartCurrent(startCurrent.format('YYYY-MM-DD'));
      setStartPrior(startPrior.format('YYYY-MM-DD'));
      setEndPrior(endPrior.format('YYYY-MM-DD'));
      setOpenPrior(startPrior.format('YYYY-MM-DD'));
    } else {
      setFieldsDisabled(false);
      setShowConfirmBox(false);
      return;
    }

    setFieldsDisabled(true);
    setShowConfirmBox(true);
  };

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
    containerName: string
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("containerName", containerName);

    try {
      const response = await fetch("/api/app_uploadBlob", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      if (response.ok) {
        alert("Upload successful!");
        fetchBlobsFromAllContainers();
      } else {
        alert(`Upload failed: ${result.message || "Unknown error"}`);
      }
    } catch (error) {
      alert("Upload failed.");
    }
  };

  const handleDownloadSelected = async (container: string) => {
    const files = selectedBlobs.filter(b => b.container === container);
    for (const blob of files) {
      try {
        const response = await fetch(`/api/app_downloadBlobs?containerName=${blob.container}&blobName=${encodeURIComponent(blob.name)}`);
        if (!response.ok) throw new Error();
        const blobData = await response.blob();
        const url = window.URL.createObjectURL(blobData);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", blob.name);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } catch {
        alert(`Error downloading ${blob.name}`);
      }
    }
  };

  return (
    <div style={{ padding: '1rem', border: '1px solid #ddd', borderRadius: '4px' }}>
      <Typography variant="h5" gutterBottom>Blob Viewer</Typography>
      <Box marginBottom={2}>
        <Button variant="contained" color="secondary" onClick={fetchBlobsFromAllContainers} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </Button>
      </Box>

      <Box display="flex" justifyContent="center" mt={4}>
        <Card variant="outlined" sx={{ padding: 4, width: '650px' }}>
          <Typography variant="h6" gutterBottom>Reporting Period Details</Typography>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={5}><Typography>End Date for Current Period:</Typography></Grid>
            <Grid item xs={7}><TextField type="date" fullWidth size="small" value={endCurrent} onChange={handleEndCurrentChange} /></Grid>

            <Grid item xs={5}><Typography>Duration of Current Period:</Typography></Grid>
            <Grid item xs={3}><TextField type="date" fullWidth size="small" value={startCurrent} disabled={fieldsDisabled} onChange={e => setStartCurrent(e.target.value)} /></Grid>
            <Grid item xs={1} textAlign="center"><Typography>to</Typography></Grid>
            <Grid item xs={3}><TextField type="date" fullWidth size="small" value={endCurrent} disabled /></Grid>

            <Grid item xs={5}><Typography>End Date for Prior Period:</Typography></Grid>
            <Grid item xs={7}><TextField type="date" fullWidth size="small" value={endPrior} disabled={fieldsDisabled} onChange={e => setEndPrior(e.target.value)} /></Grid>

            <Grid item xs={5}><Typography>Duration of Prior Period:</Typography></Grid>
            <Grid item xs={3}><TextField type="date" fullWidth size="small" value={startPrior} disabled={fieldsDisabled} onChange={e => setStartPrior(e.target.value)} /></Grid>
            <Grid item xs={1} textAlign="center"><Typography>to</Typography></Grid>
            <Grid item xs={3}><TextField type="date" fullWidth size="small" value={endPrior} disabled /></Grid>

            <Grid item xs={5}><Typography>Opening Date for Prior Period:</Typography></Grid>
            <Grid item xs={7}><TextField type="date" fullWidth size="small" value={openPrior} disabled={fieldsDisabled} onChange={e => setOpenPrior(e.target.value)} /></Grid>
          </Grid>

          {showConfirmBox && (
            <Box mt={3}>
              <Alert
                icon={<InfoIcon fontSize="inherit" />}
                severity="info"
                action={
                  <>
                    <Button size="small" onClick={() => setShowConfirmBox(false)}>DATES ARE OK</Button>
                    <Button size="small" onClick={() => { setFieldsDisabled(false); setShowConfirmBox(false); }}>EDIT DATES</Button>
                  </>
                }
              >
                The dates have been auto-populated based on your selection. Are these dates correct, or do you wish to edit them manually?
              </Alert>
            </Box>
          )}
        </Card>
      </Box>

      {error && (
        <Typography variant="body1" color="error" gutterBottom>{error}</Typography>
      )}

      {CONTAINER_NAMES.map(containerName => {
        const blobItems = blobsByContainer[containerName] || [];
        return (
          <Card key={containerName} sx={{ marginBottom: 2 }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="h6" gutterBottom>
                  Container: {CONTAINER_LABELS[containerName] || containerName}
                </Typography>
                {containerName === 'silver' && (
                  <>
                    <input
                      type="file"
                      id={`file-input-${containerName}`}
                      style={{ display: 'none' }}
                      onChange={e => handleFileUpload(e, containerName)}
                    />
                    <label htmlFor={`file-input-${containerName}`}>
                      <Button variant="outlined" color="primary" size="small" component="span">Upload</Button>
                    </label>
                  </>
                )}
                {containerName === 'gold' && (
                  <Button
                    variant="outlined"
                    color="success"
                    size="small"
                    onClick={() => handleDownloadSelected(containerName)}
                    disabled={selectedBlobs.filter(b => b.container === containerName).length === 0}
                  >
                    Download
                  </Button>
                )}
              </Box>

              {blobItems.length === 0 ? (
                <Typography variant="body2">No files present</Typography>
              ) : (
                <List dense>
                  {blobItems.map(blob => (
                    <ListItem key={blob.name} disablePadding>
                      <Checkbox
                        checked={selectedBlobs.some(b => b.name === blob.name && b.container === containerName)}
                        onChange={() => toggleSelection(containerName, blob)}
                      />
                      <ListItemText
                        primary={<Link href={blob.url} target="_blank" rel="noopener noreferrer">{blob.name}</Link>}
                        primaryTypographyProps={{ align: 'center' }}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
});

export default BlobList;
