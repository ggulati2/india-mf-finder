import { NextRequest, NextResponse } from "next/server";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const scheme_id = searchParams.get("scheme_id");
  const years = searchParams.get("years") || "5";
  if (!scheme_id) return NextResponse.json({ error: "scheme_id required" }, { status: 400 });
  const r = await fetch(`${API_BASE_URL}/api/v1/analytics/${scheme_id}/history?years=${years}`);
  const data = await r.json();
  return NextResponse.json(data, { status: r.status });
}
