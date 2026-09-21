import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const investmentMode = searchParams.get("investment_mode") || "lump-sum";
  const riskAppetite = searchParams.get("risk_appetite") || "medium";
  const category = searchParams.get("category") || "";

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/recommendations/funds?investment_mode=${investmentMode}&risk_appetite=${riskAppetite}&category=${category}`
    );
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch funds" }, { status: 500 });
  }
}
