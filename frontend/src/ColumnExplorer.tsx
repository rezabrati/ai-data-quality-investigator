import { useEffect, useState } from "react";
import NumericCharts from "./NumericCharts";
import CategoricalChart from "./CategoricalChart";


type OutlierSummary =
  | {
      method: string;
      count: number;
      percent: number;
      lower_bound: number;
      upper_bound: number;
    }
  | {
      method: string;
      status: "skipped";
      reason: string;
    };

type NumericSummary = {
  min: number;
  max: number;
  mean: number;
  median: number;
  std: number | null;
  q1: number;
  q3: number;
  skewness: number | null;
  finite_count: number;
  infinite_count: number;
  outliers: OutlierSummary;
};

export type ColumnProfile = {
  name: string;
  dtype: string;
  missing_count: number;
  blank_count: number;
  placeholder_count: number;
  unique_count: number;
  numeric_summary: NumericSummary | null;
};

type Frequencies = {
  column: string;
  percent_basis: string;
  categories: {
    value: string;
    count: number;
    percent: number;
  }[];
  other_count: number;
};

type Props = {
  datasetId: string;
  columns: ColumnProfile[];
};

function formatNumber(value: number | null): string {
  if (value === null) return "Not available";

  return value.toLocaleString(undefined, {
    maximumFractionDigits: 3,
  });
}

export default function ColumnExplorer({ datasetId, columns }: Props) {
  const [selectedName, setSelectedName] = useState(
    columns[0]?.name ?? ""
  );
  const [frequencies, setFrequencies] = useState<Frequencies | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = columns.find(
    (column) => column.name === selectedName
  );

  const numeric = selected?.numeric_summary;
  const showFrequencies = Boolean(selected) && !numeric;

  const numericMeasurements: [string, number | null][] = numeric
    ? [
        ["Minimum", numeric.min],
        ["Maximum", numeric.max],
        ["Mean", numeric.mean],
        ["Median", numeric.median],
        ["Standard deviation", numeric.std],
        ["Skewness", numeric.skewness],
      ]
    : [];

  useEffect(() => {
    if (!selectedName || !showFrequencies) return;

    const controller = new AbortController();

    async function loadFrequencies() {
      setLoading(true);
      setError(null);
      setFrequencies(null);

      try {
        const params = new URLSearchParams({
          column: selectedName,
          limit: "10",
        });

        const response = await fetch(
          `/api/datasets/${datasetId}/categories?${params}`,
          { signal: controller.signal }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            typeof data.detail === "string"
              ? data.detail
              : "Could not load value frequencies."
          );
        }

        if (!controller.signal.aborted) {
          setFrequencies(data);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error ? err.message : "Request failed."
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadFrequencies();

    // Cancel the request when switching columns or leaving the component.
    return () => controller.abort();
  }, [datasetId, selectedName, showFrequencies]);

  return (
    <section className="column-explorer">
      <h3>Column explorer</h3>
      <p>
        Select a column to inspect its quality, numeric statistics,
        or most frequent values.
      </p>

      <label htmlFor="explorer-column">Column</label>
      <select
        id="explorer-column"
        value={selectedName}
        onChange={(event) => {
          setSelectedName(event.target.value);
          setFrequencies(null);
          setError(null);
        }}
      >
        {columns.map((column) => (
          <option key={column.name} value={column.name}>
            {column.name}
          </option>
        ))}
      </select>

      {selected && (
        <>
          <p>
            Inferred type: <code>{selected.dtype}</code>
          </p>

          <dl className="column-stats">
            <div>
              <dt>Missing</dt>
              <dd>{selected.missing_count.toLocaleString()}</dd>
            </div>

            <div>
              <dt>Blank</dt>
              <dd>{selected.blank_count.toLocaleString()}</dd>
            </div>

            <div>
              <dt>Potential placeholders</dt>
              <dd>{selected.placeholder_count.toLocaleString()}</dd>
            </div>

            <div>
              <dt>Unique values</dt>
              <dd>{selected.unique_count.toLocaleString()}</dd>
            </div>
          </dl>
        </>
      )}
      
      {numeric && (
        <NumericCharts
            key={`${datasetId}-${selectedName}`}
            datasetId={datasetId}
            column={selectedName}
        />
        )}

      {numeric && (
        <details key={selectedName} className="numeric-details">
          <summary>Numeric statistics</summary>

          <dl className="column-stats">
            {numericMeasurements.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{formatNumber(value)}</dd>
              </div>
            ))}
          </dl>

          {"count" in numeric.outliers ? (
            <p>
              Potential IQR outliers:{" "}
              <strong>
                {numeric.outliers.count.toLocaleString()}
              </strong>{" "}
              ({numeric.outliers.percent.toFixed(2)}% of finite values).
            </p>
          ) : (
            <p>
              IQR outlier check skipped: {numeric.outliers.reason}
            </p>
          )}

          <p>
            Infinite values: {numeric.infinite_count.toLocaleString()}
          </p>
        </details>
      )}

      {showFrequencies && loading && (
        <p role="status">Loading value frequencies…</p>
      )}

      {showFrequencies && error && <p role="alert">{error}</p>}

      {showFrequencies &&
        frequencies &&
        frequencies.column === selectedName && (
            <div className="categorical-layout">
            <CategoricalChart
                categories={frequencies.categories}
                otherCount={frequencies.other_count}
            />

            <article className="chart-card">
                <h4>Most frequent values</h4>
                <p>Percentage basis: {frequencies.percent_basis}</p>

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
                    {frequencies.categories.map((category, index) => (
                        <tr key={`${category.value}-${index}`}>
                        <td>
                            <code>{JSON.stringify(category.value)}</code>
                        </td>
                        <td>{category.count.toLocaleString()}</td>
                        <td>{category.percent.toFixed(2)}%</td>
                        </tr>
                    ))}
                    </tbody>
                </table>
                </div>

                <p>
                Rows in unlisted values:{" "}
                {frequencies.other_count.toLocaleString()}
                </p>
            </article>
            </div>
      )}
    </section>
  );
}