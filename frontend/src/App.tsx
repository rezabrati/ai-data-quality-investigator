import { useState } from "react";
import Markdown from "react-markdown";
type InvestigationResult = {
  dataset_id: string;
  profile: {
    dataset_id: string;
    summary: {
      row_count: number;
      column_count: number;
      duplicate_row_count: number;
      findings: {
        code: string;
        column: string | null;
        count: number;
        message: string;
      }[];
    };
  };
  category_frequencies: {
    column: string;
    percent_basis: string;
    categories: {
      value: string;
      count: number;
      percent: number;
    }[];
    other_count: number;
  } | null;
  suggested_investigations: string;
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [targetColumn, setTargetColumn] = useState("");
  const [taskType, setTaskType] = useState<
     "" | "classification" | "regression"
  >("");
  const [investigating, setInvestigating] = useState(false);
  const [investigation, setInvestigation] = useState<InvestigationResult | null>(null);

  async function uploadDataset() {
    if (!file || uploading || investigating) return;

    const target = targetColumn.trim();

    if (Boolean(target) !== Boolean(taskType)) {
      setError("Provide both target column and task type, or leave both empty.");
      return;
    }

    setUploading(true);
    setError(null);
    setDatasetId(null);
    setInvestigation(null);

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

  async function runInvestigation() {
    if (!datasetId || uploading || investigating) return;
  
    setInvestigating(true);
    setInvestigation(null);
    setError(null);
  
    try {
      const response = await fetch(
        `/api/datasets/${datasetId}/investigate`,
        { method: "POST" }
      );
  
      const data = await response.json();
  
      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Investigation failed (${response.status}).`
        );
      }
  
      setInvestigation(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not investigate the dataset."
      );
    } finally {
      setInvestigating(false);
    }
  }
  ////
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Dataset controls">
        <section className="card">
          <h2>Upload your dataset</h2>
          <p>Choose a CSV file with comma or semicolon separators.</p>

          <label htmlFor="dataset">CSV file</label>
          <input
            id="dataset"
            type="file"
            accept=".csv"
            disabled={uploading || investigating}
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setDatasetId(null);
              setInvestigation(null);
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
            disabled={uploading || investigating}
            onChange={(event) => {
              setTargetColumn(event.target.value);
              setDatasetId(null);
              setInvestigation(null);
              setError(null);
            }}
          />

          <label htmlFor="task-type">Task type (optional)</label>
          <select
            id="task-type"
            value={taskType}
            disabled={uploading || investigating}
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
              setInvestigation(null);
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
            disabled={!file || uploading || investigating}
          >
            {uploading ? "Uploading…" : "Upload dataset"}
          </button>

          {error && <p role="alert">{error}</p>}

          {datasetId && (
            <>
              <p role="status">
                Dataset uploaded successfully.
                <br />
                ID: <code>{datasetId}</code>
              </p>

              <button
                type="button"
                onClick={runInvestigation}
                disabled={uploading || investigating}
              >
                {investigating ? "Investigating…" : "Run investigation"}
              </button>
            </>
          )}

          {investigating && (
            <p role="status">
              Inspecting the dataset and generating follow-up questions…
            </p>
          )}
        </section>
      </aside>

      <main className="main-content">
        <header>
          <span className="badge">AI-powered investigation</span>
          <h1>AI Data Quality Investigator</h1>
          <p>
            Inspect your data, review quality findings, and explore
            suggested next investigations.
          </p>
        </header>

        {investigation === null && (
          <section className="card empty-state">
            <h2>
              {investigating
                ? "Investigation in progress"
                : "Your results will appear here"}
            </h2>
            <p>
              {investigating
                ? "The agents are inspecting your dataset. Please wait."
                : "Upload a CSV using the sidebar, then run an investigation."}
            </p>
          </section>
        )}

        {investigation !== null && (
          <section className="card">
            <h2>Investigation results</h2>

            <div className="metrics">
              <div className="metric">
                <span>Rows</span>
                <strong>
                  {investigation.profile.summary.row_count.toLocaleString()}
                </strong>
              </div>

              <div className="metric">
                <span>Columns</span>
                <strong>
                  {investigation.profile.summary.column_count}
                </strong>
              </div>

              <div className="metric">
                <span>Duplicate rows</span>
                <strong>
                  {investigation.profile.summary.duplicate_row_count}
                </strong>
              </div>

              <div className="metric">
                <span>Findings</span>
                <strong>
                  {investigation.profile.summary.findings.length}
                </strong>
              </div>
            </div>

            <h3>Quality findings</h3>
            <p>
              These checks identify review candidates. Outliers and
              placeholders are not automatically errors.
            </p>

            {investigation.profile.summary.findings.length === 0 ? (
              <p>No findings were reported by the implemented checks.</p>
            ) : (
              <ul className="findings">
                {investigation.profile.summary.findings.map(
                  (finding, index) => (
                    <li
                      key={`${finding.code}-${finding.column}-${index}`}
                    >
                      {finding.message}
                    </li>
                  )
                )}
              </ul>
            )}

            {investigation.category_frequencies && (
              <div className="category-results">
                <h3>
                  Category investigation:{" "}
                  {investigation.category_frequencies.column}
                </h3>

                <p>
                  Percentage basis:{" "}
                  {investigation.category_frequencies.percent_basis}
                </p>

                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th scope="col">Value</th>
                        <th scope="col">Rows</th>
                        <th scope="col">Percentage</th>
                      </tr>
                    </thead>

                    <tbody>
                      {investigation.category_frequencies.categories.map(
                        (category, index) => (
                          <tr key={`${category.value}-${index}`}>
                            <td>
                              <code>
                                {JSON.stringify(category.value)}
                              </code>
                            </td>
                            <td>{category.count.toLocaleString()}</td>
                            <td>{category.percent.toFixed(2)}%</td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>

                <p>
                  Rows in unlisted categories:{" "}
                  {investigation.category_frequencies.other_count.toLocaleString()}
                </p>
              </div>
            )}

            <div className="ai-suggestions">
              <h3>Suggested investigations</h3>
              <p className="ai-label">
                AI-generated questions for further review. These checks
                have not been performed.
              </p>

              <Markdown skipHtml>
                {investigation.suggested_investigations}
              </Markdown>
            </div>

            <details>
              <summary>View full API response</summary>
              <pre className="json-result">
                {JSON.stringify(investigation, null, 2)}
              </pre>
            </details>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;