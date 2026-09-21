import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const schemeIds = searchParams.get("scheme_ids") || "";

  if (!schemeIds) {
    return NextResponse.json({ error: "scheme_ids required" }, { status: 400 });
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/overlap/matrix?scheme_ids=${schemeIds}`
    );
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch overlap matrix" }, { status: 500 });
  }
}
