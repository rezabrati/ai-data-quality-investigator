export type TargetProfile = {
    column: string;
    task_type: "classification" | "regression";
    missing_count: number;
    labeled_count?: number;
    class_count?: number;
    class_distribution?: {
      value: string;
      count: number;
      percent: number;
    }[];
  };
  
  type Props = {
    target: TargetProfile | null;
  };
  
  export default function TargetSummary({ target }: Props) {
    if (!target) return null;
  
    const classes = target.class_distribution ?? [];
    const visibleClasses = classes.slice(0, 10);
  
    return (
      <section className="target-summary">
        <h3>Target overview</h3>
  
        <p>
          Target: <strong>{target.column}</strong>
          {" · "}
          Task: {target.task_type}
          {" · "}
          Missing labels: {target.missing_count.toLocaleString()}
        </p>
  
        {target.task_type === "classification" && (
          <>
            <p>
              Classes: {target.class_count ?? classes.length}
              {" · "}
              Labeled rows: {target.labeled_count?.toLocaleString() ?? "—"}
            </p>
  
            {classes.length === 0 ? (
              <p>No labeled classes were reported.</p>
            ) : (
              <>
                <p>Percentages are based on non-missing target values.</p>
  
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th scope="col">Class</th>
                        <th scope="col">Rows</th>
                        <th scope="col">Share</th>
                      </tr>
                    </thead>
  
                    <tbody>
                      {visibleClasses.map((item, index) => (
                        <tr key={`${item.value}-${index}`}>
                          <td>
                            <code>{JSON.stringify(item.value)}</code>
                          </td>
                          <td>{item.count.toLocaleString()}</td>
                          <td>
                            <div className="class-share">
                              <progress
                                max={100}
                                value={item.percent}
                                aria-label={`Class ${item.value}: ${item.percent}%`}
                              />
                              <span>{item.percent.toFixed(2)}%</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
  
                {classes.length > 10 && (
                  <p>
                    Showing the first 10 of {classes.length} classes.
                    The full distribution is in the API response.
                  </p>
                )}
              </>
            )}
          </>
        )}
      </section>
    );
  }