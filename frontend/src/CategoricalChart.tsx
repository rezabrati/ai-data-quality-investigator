import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

type Props = {
  categories: {
    value: string;
    count: number;
    percent: number;
  }[];
  otherCount: number;
};

export default function CategoricalChart({
  categories,
  otherCount,
}: Props) {
  const slices = categories.map((category) => ({
    name: JSON.stringify(category.value),
    value: category.count,
  }));

  if (otherCount > 0) {
    slices.push({
      name: "Unlisted values (combined)",
      value: otherCount,
    });
  }

  const total = slices.reduce((sum, slice) => sum + slice.value, 0);

  if (total === 0) {
    return <p>No non-missing values are available to plot.</p>;
  }

  const option: EChartsOption = {
    animation: false,
    aria: { enabled: true },

    color: [
      "#6366f1",
      "#14b8a6",
      "#f59e0b",
      "#ec4899",
      "#3b82f6",
      "#8b5cf6",
      "#84cc16",
      "#f97316",
      "#06b6d4",
      "#a855f7",
      "#94a3b8",
    ],

    tooltip: {
      trigger: "item",
      renderMode: "richText",
      formatter: "{b}\n{c} rows ({d}%)",
    },

    legend: {
      type: "scroll",
      bottom: 0,
      left: "center",
      selectedMode: false,
      textStyle: {
        fontSize: 13,
      },
    },

    series: [
      {
        name: "Category distribution",
        type: "pie",
        radius: ["45%", "68%"],
        center: ["50%", "43%"],
        percentPrecision: 2,

        itemStyle: {
          borderColor: "#ffffff",
          borderWidth: 2,
        },

        label: {
          show: false,
        },

        labelLine: {
          show: false,
        },

        emphasis: {
          scale: true,
          label: {
            show: true,
            position: "center",
            formatter: "{d}%",
            fontSize: 24,
            fontWeight: "bold",
          },
        },

        data: slices,
      },
    ],
  };

  return (
    <article className="chart-card categorical-chart">
      <h4>Category distribution</h4>
      <p>
        Share of non-missing rows. Hover over a slice for its
        category, count, and percentage.
      </p>

      <ReactECharts
        option={option}
        notMerge
        style={{ height: 360 }}
      />

      {otherCount > 0 && (
        <p>
          Categories outside the displayed top values are grouped
          into “Unlisted values (combined)”.
        </p>
      )}
    </article>
  );
}