// ============================================================================
// Healthcare Revenue Cycle Intelligence - Power Query (M) Ingestion Scripts
// Update BasePath parameter to your local repository data/processed folder.
// ============================================================================

let
    BasePath = "C:\path\to\healthcare-revenue-cycle-intelligence\data\processed\",

    LoadFactClaims = let
        Source = Csv.Document(File.Contents(BasePath & "fact_claims.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
        PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
        TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
            {"claim_id", Int64.Type},
            {"visit_id", Int64.Type},
            {"date_key", Int64.Type},
            {"department_id", Int64.Type},
            {"payer_id", Int64.Type},
            {"claim_status", type text},
            {"billed_amount", type number},
            {"paid_amount", type number}
        }),
        FilteredValid = Table.SelectRows(TypedTable, each [billed_amount] >= 0 and [paid_amount] >= 0)
    in
        FilteredValid,

    LoadDimDate = let
        Source = Csv.Document(File.Contents(BasePath & "dim_date.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
        PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
        TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
            {"date_key", Int64.Type},
            {"full_date", type date},
            {"year", Int64.Type},
            {"quarter", Int64.Type},
            {"month_num", Int64.Type},
            {"month_name", type text},
            {"year_month", type text}
        })
    in
        TypedTable
in
    [fact_claims = LoadFactClaims, dim_date = LoadDimDate]
