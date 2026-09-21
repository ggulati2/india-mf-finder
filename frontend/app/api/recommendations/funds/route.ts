import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const investmentAmount = searchParams.get("investment_amount") || "100000";
  const investmentMode = searchParams.get("investment_mode") || "lump-sum";
  const horizonYears = searchParams.get("horizon_years") || "5";
  const riskAppetite = searchParams.get("risk_appetite") || "medium";
  const category = searchParams.get("category") || "";
  const completeOnly = searchParams.get("complete_only") === "true" ? "true" : "false";

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/recommendations/funds?investment_amount=${investmentAmount}&investment_mode=${investmentMode}&horizon_years=${horizonYears}&risk_appetite=${riskAppetite}&category=${category}&complete_only=${completeOnly}`
    );
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch funds" }, { status: 500 });
  }
}
