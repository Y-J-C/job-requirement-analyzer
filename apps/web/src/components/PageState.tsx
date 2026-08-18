type PageStateProps = {
  kind?: "loading" | "error";
  title: string;
  message: string;
};


export function PageState({ kind = "loading", title, message }: PageStateProps) {
  const isError = kind === "error";
  return (
    <main className="shell page-state-shell">
      <section
        className={`page-state page-state-${kind}`}
        role={isError ? "alert" : "status"}
        aria-busy={isError ? undefined : true}
        aria-live="polite"
      >
        <span className="page-state-mark" aria-hidden="true">{isError ? "!" : "…"}</span>
        <div>
          <h1>{title}</h1>
          <p>{message}</p>
        </div>
      </section>
    </main>
  );
}
