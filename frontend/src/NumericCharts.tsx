import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

type BoxPlot =
  | {
      status: "available";
      q1: number;
      median: number;
      q3: number;
      lower_whisker: number;
      upper_whisker: number;
      outlier_count: number;
    }
  | {
      status: "skipped";
      reason: string;
    };

type Distribution = {
  column: string;
  finite_count: number;
  missing_count: number;
  infinite_count: number;
  histogram: {
    lower: number;
    upper: number;
    count: number;
  }[];
  boxplot: BoxPlot;
};

type Props = {
  datasetId: string;
  column: string;
};

function formatValue(value: number): string {
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

export default function NumericCharts({ datasetId, column }: Props) {
  const [data, setData] = useState<Distribution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadDistribution() {
      setLoading(true);
      setError(null);
      setData(null);

      try {
        const params = new URLSearchParams({
          column,
          bins: "20",
        });

        const response = await fetch(
          `/api/datasets/${datasetId}/numeric-distribution?${params}`,
          { signal: controller.signal }
        );

        const result = await response.json();

        if (!response.ok) {
          throw new Error(
            typeof result.detail === "string"
              ? result.detail
              : "Could not load numeric charts."
          );
        }

        if (!controller.signal.aborted) {
          setData(result);
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

    void loadDistribution();

    return () => controller.abort();
  }, [datasetId, column]);

  if (loading) return <p role="status">Loading numeric charts…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (!data || data.column !== column) return null;

  const histogramOption: EChartsOption = {
    animation: false,
    aria: { enabled: true },
    tooltip: {
      trigger: "axis",
      renderMode: "richText",
    },
    grid: {
      left: 65,
      right: 20,
      top: 25,
      bottom: 65,
    },
    xAxis: {
      type: "category",
      name: "Value interval",
      nameLocation: "middle",
      nameGap: 40,
      data: data.histogram.map(
        (bin, index) =>
          `[${formatValue(bin.lower)}, ${formatValue(bin.upper)}${
            index === data.histogram.length - 1 ? "]" : ")"
          }`
      ),
      axisLabel: {
        show: false,
      },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "Rows",
      minInterval: 1,
    },
    series: [
      {
        name: "Rows",
        type: "bar",
        data: data.histogram.map((bin) => bin.count),
        barCategoryGap: "0%",
        itemStyle: {
          color: "#6366f1",
          borderColor: "#ffffff",
          borderWidth: 1,
        },
      },
    ],
  };

  const box = data.boxplot;

  const boxplotOption: EChartsOption | null =
    box.status === "available"
      ? {
          animation: false,
          aria: { enabled: true },
          tooltip: {
            trigger: "item",
            renderMode: "richText",
          },
          grid: {
            left: 65,
            right: 30,
            top: 25,
            bottom: 45,
          },
          xAxis: {
            type: "value",
            scale: true,
          },
          yAxis: {
            type: "category",
            data: [column],
            axisLabel: { show: false },
            axisTick: { show: false },
          },
          series: [
            {
              name: column,
              type: "boxplot",
              layout: "horizontal",
              data: [
                [
                  box.lower_whisker,
                  box.q1,
                  box.median,
                  box.q3,
                  box.upper_whisker,
                ],
              ],
              itemStyle: {
                color: "#e0e7ff",
                borderColor: "#4338ca",
                borderWidth: 2,
              },
            },
          ],
        }
      : null;

  return (
    <div className="numeric-charts">
      <article className="chart-card">
        <h4>Histogram</h4>
        <p>
          {data.finite_count.toLocaleString()} finite values.
          Hover over a bar to see its interval and count.
        </p>

        <ReactECharts
          option={histogramOption}
          notMerge
          style={{ height: 300 }}
        />
      </article>

      <article className="chart-card">
        <h4>Box plot</h4>

        {boxplotOption ? (
          <>
            <ReactECharts
              option={boxplotOption}
              notMerge
              style={{ height: 220 }}
            />

            {box.status === "available" && (
              <p>
                Whiskers use the 1.5 × IQR rule.
                {" "}
                {box.outlier_count.toLocaleString()} potential outliers
                are counted but not drawn as individual points.
              </p>
            )}
          </>
        ) : (
          <p>
            Box plot skipped:{" "}
            {box.status === "skipped" ? box.reason : ""}
          </p>
        )}
      </article>
    </div>
  );
}