import { useState } from "react";

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [targetColumn, setTargetColumn] = useState("");
  const [taskType, setTaskType] = useState<
     "" | "classification" | "regression"
  >("");

  async function uploadDataset() {
    if (!file || uploading) return;

    const target = targetColumn.trim();

    if (Boolean(target) !== Boolean(taskType)) {
      setError("Provide both target column and task type, or leave both empty.");
      return;
    }

    setUploading(true);
    setError(null);
    setDatasetId(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      if (target && taskType) {
        formData.append("target_column", target);
        formData.append("task_type", taskType);
      }

      const response = await fetch("/api/datasets/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Upload failed (${response.status}).`
        );
      }

      if (typeof data.dataset_id !== "string") {
        throw new Error("The server did not return a dataset ID.");
      }

      setDatasetId(data.dataset_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not upload the dataset."
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="container">
      <header>
        <span className="badge">AI-powered investigation</span>
        <h1>AI Data Quality Investigator</h1>
        <p>
          Inspect your data, review quality findings, and explore
          suggested next investigations.
        </p>
      </header>

      <section className="card">
        <h2>Upload your dataset</h2>
        <p>Choose a CSV file with comma or semicolon separators.</p>

        <label htmlFor="dataset">CSV file</label>
        <input
          id="dataset"
          type="file"
          accept=".csv"
          disabled={uploading}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setDatasetId(null);
            setError(null);
          }}
        />

        {file && (
          <div className="selection">
            <strong>{file.name}</strong>
            <span>{(file.size / 1_000_000).toFixed(4)} MB</span>
          </div>
        )}

        <label htmlFor="target-column">Target column (optional)</label>
        <input
          id="target-column"
          type="text"
          placeholder="For example: y"
          value={targetColumn}
          disabled={uploading}
          onChange={(event) => {
            setTargetColumn(event.target.value);
            setDatasetId(null);
            setError(null);
          }}
        />

        <label htmlFor="task-type">Task type (optional)</label>
        <select
          id="task-type"
          value={taskType}
          disabled={uploading}
          onChange={(event) => {
            const value = event.target.value;
            if (
              value === "" ||
              value === "classification" ||
              value === "regression"
            ) {
              setTaskType(value);
            }
            setDatasetId(null);
            setError(null);
          }}
        >
          <option value="">No target analysis</option>
          <option value="classification">Classification</option>
          <option value="regression">Regression</option>
        </select>

        <button
          type="button"
          onClick={uploadDataset}
          disabled={!file || uploading}
        >
          {uploading ? "Uploading…" : "Upload dataset"}
        </button>

        {error && <p role="alert">{error}</p>}

        {datasetId && (
          <p role="status">
            Dataset uploaded successfully. ID: <code>{datasetId}</code>
          </p>
        )}
      </section>
    </main>
  );
}

export default App;