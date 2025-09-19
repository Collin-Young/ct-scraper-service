import { useCallback, useEffect, useMemo, useState } from "react";

import { Link } from "react-router-dom";
import { CasesMap } from "@/components/CasesMap";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Nav from "../components/Nav";
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import { COUNTIES, townsForCounty } from "@/data/locations";
import type { CaseRecord } from "@/types";

const LIMIT = 100;
const STORAGE_KEY = "ct-scraper-api-base";
const DEFAULT_STATUS = `Select filters and click Apply Filters to load up to ${LIMIT} cases.`;

const DEFAULT_API_BASE = import.meta.env.VITE_DEFAULT_API_BASE ?? "https://geoleads.land/api";


interface Filters {
  county: string;
  town: string;
  dateFrom: string;
  dateTo: string;
}

const DEFAULT_FILTERS: Filters = {
  county: "",
  town: "",
  dateFrom: "",
  dateTo: "",
};

function sanitizeBase(value: string) {
  return value.trim().replace(/\/$/, "");
}

export default function App() {
  const defaultBase = useMemo(() => {
    if (typeof window === "undefined") {
      return DEFAULT_API_BASE;
    }
    const origin = window.location.origin.replace(/\/$/, "");
    if (origin.includes("localhost:5173")) {
      return DEFAULT_API_BASE;
    }
    return `${origin}/api`;
  }, []);


  const [baseUrl, setBaseUrl] = useState<string>(defaultBase);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [status, setStatus] = useState(DEFAULT_STATUS);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && saved.startsWith("http")) {
      if (saved.includes("157.230.11.23")) {
        setBaseUrl(defaultBase);
        localStorage.setItem(STORAGE_KEY, defaultBase);
      } else {
        setBaseUrl(saved);
      }
    } else if (defaultBase) {
      setBaseUrl(defaultBase);
    }
  }, [defaultBase]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!baseUrl || !baseUrl.startsWith("http")) return;
    localStorage.setItem(STORAGE_KEY, baseUrl);
  }, [baseUrl]);

  const townOptions = useMemo(() => townsForCounty(filters.county), [filters.county]);

  const fetchCases = useCallback(
    async (currentFilters: Filters) => {
      let sanitized = sanitizeBase(baseUrl);
      if (!sanitized || !sanitized.startsWith("http")) {
        setError("Provide a valid API base URL.");
        setStatus("Provide a valid API base URL.");
        return;
      }

      if (sanitized !== baseUrl) {
        setBaseUrl(sanitized);
      }

      setIsLoading(true);
      setError(null);
      setStatus("Loading cases...");

      const params = new URLSearchParams({ limit: LIMIT.toString() });
      if (currentFilters.county) params.set("county", currentFilters.county);
      if (currentFilters.town) params.set("town", currentFilters.town);
      if (currentFilters.dateFrom) params.set("date_from", currentFilters.dateFrom);
      if (currentFilters.dateTo) params.set("date_to", currentFilters.dateTo);

      try {
        const response = await fetch(`${sanitized}/cases?${params.toString()}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload = await response.json();
        const rows = Array.isArray(payload) ? (payload as CaseRecord[]) : [];
        setCases(rows);
        setStatus(`Showing ${rows.length} case(s) (max ${LIMIT})`);
        setLastUpdated(new Date().toISOString());
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        setStatus(`Error loading cases: ${message}`);
        setCases([]);
      } finally {
        setIsLoading(false);
      }
    },
    [baseUrl]
  );

  const handleApplyFilters = () => {
    fetchCases(filters);
  };

  const handleRefresh = () => {
    fetchCases(filters);
  };

  const handleClearFilters = () => {
    setFilters(DEFAULT_FILTERS);
    fetchCases(DEFAULT_FILTERS);
  };

  const formattedLastUpdated = useMemo(() => {
    if (!lastUpdated) return "";
    return new Date(lastUpdated).toLocaleString();
  }, [lastUpdated]);

  const hasCases = cases.length > 0;

  return (
    <div className="min-h-screen bg-gray-900">

      <header className="border-b bg-gray-900/90 backdrop-blur-sm border-gray-700">
        <Nav />
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-6 bg-gray-900">
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="grid gap-2">
                <Label htmlFor="county" className="text-white">County</Label>
                <Select
                  value={filters.county || "__all"}
                  onValueChange={(value) =>
                    setFilters((prev) => ({
                      ...prev,
                      county: value === "__all" ? "" : value,
                      town: value === "__all" ? prev.town : "",
                    }))
                  }
                >
                  <SelectTrigger id="county" className="bg-gray-800 border-gray-600 text-white">
                    <SelectValue placeholder="All counties" />
                  </SelectTrigger>
                  <SelectContent className="z-[2000] bg-gray-800 border-gray-600 text-white">
                    <SelectItem value="__all">All counties</SelectItem>
                    {COUNTIES.map((county) => (
                      <SelectItem key={county} value={county}>
                        {county}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="town" className="text-white">Town</Label>
                <Select
                  value={filters.town || "__all"}
                  onValueChange={(value) =>
                    setFilters((prev) => ({
                      ...prev,
                      town: value === "__all" ? "" : value,
                    }))
                  }
                >
                  <SelectTrigger id="town" className="bg-gray-800 border-gray-600 text-white">
                    <SelectValue placeholder="All towns" />
                  </SelectTrigger>
                  <SelectContent className="z-[2000] bg-gray-800 border-gray-600 text-white">
                    <SelectItem value="__all">All towns</SelectItem>
                    {townOptions.map((town) => (
                      <SelectItem key={town} value={town}>
                        {town}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="date-from" className="text-white">From Date</Label>
                <Input
                  id="date-from"
                  type="date"
                  value={filters.dateFrom}
                  max={filters.dateTo || undefined}
                  onChange={(event) =>
                    setFilters((prev) => ({ ...prev, dateFrom: event.target.value }))
                  }
                  className="bg-gray-800 border-gray-600 text-white"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="date-to" className="text-white">To Date</Label>
                <Input
                  id="date-to"
                  type="date"
                  min={filters.dateFrom || undefined}
                  value={filters.dateTo}
                  onChange={(event) =>
                    setFilters((prev) => ({ ...prev, dateTo: event.target.value }))
                  }
                  className="bg-gray-800 border-gray-600 text-white"
                />
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between bg-gray-800 border-t border-gray-700">
            <div className="flex items-center gap-3">
              <Button onClick={handleApplyFilters} disabled={isLoading} className="bg-[#5227FF] hover:bg-[#4F20E8] text-white">
                {isLoading ? "Loading..." : "Apply Filters"}
              </Button>
              <Button
                variant="outline"
                onClick={handleClearFilters}
                disabled={isLoading}
                className="border-gray-600 text-white hover:bg-gray-700"
              >
                Clear
              </Button>
            </div>
            <div className="text-sm text-gray-400">{status}</div>
          </CardFooter>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardHeader className="pb-0">
            <CardTitle className="text-white">Map View</CardTitle>
          </CardHeader>
          <CardContent className="pt-4 bg-gray-800">
            <CasesMap cases={cases} />
          </CardContent>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">Cases</CardTitle>
          </CardHeader>
          <CardContent className="p-0 bg-gray-800">
            <TableContainer component={Paper} sx={{ backgroundColor: '#1f2937', border: '1px solid #374151', overflowX: 'auto' }}>
              <Table sx={{ minWidth: 650, color: '#f9fafb' }} aria-label="cases table">
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#374151' }}>
                    <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>Docket</TableCell>
                    <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>Town</TableCell>
                    <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>County</TableCell>
                    <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>Property</TableCell>
                    <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>Case Type</TableCell>
                    <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>Last Action</TableCell>
                    <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>Created</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {hasCases ? (
                    cases.map((row, index) => {
                      const created = row.created_at
                        ? new Date(`${row.created_at}${row.created_at.endsWith("Z") ? "" : "Z"}`).toLocaleString()
                        : "";
                      const docketContent = row.case_url ? (
                        <a
                          href={row.case_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#5227FF] underline-offset-4 hover:underline"
                        >
                          {row.docket_no}
                        </a>
                      ) : (
                        row.docket_no ?? ""
                      );

                      return (
                        <TableRow
                          key={`${row.docket_no ?? "case"}-${index}`}
                          sx={{
                            '&:last-child td, &:last-child th': { border: 0 },
                            '&:hover': { backgroundColor: 'rgba(55, 65, 81, 0.5)' },
                            borderColor: '#4b5563'
                          }}
                        >
                          <TableCell component="th" scope="row" sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>
                            {docketContent}
                          </TableCell>
                          <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>{row.town ?? ""}</TableCell>
                          <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>{row.county ?? ""}</TableCell>
                          <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>{row.property_address ?? ""}</TableCell>
                          <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>{row.case_type ?? ""}</TableCell>
                          <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>{row.last_action_date ?? ""}</TableCell>
                          <TableCell sx={{ color: '#f9fafb', borderColor: '#4b5563' }}>{created}</TableCell>
                        </TableRow>
                      );
                    })
                  ) : (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ color: '#9ca3af', height: '6rem' }}>
                        {error ? error : "No cases match your filter."}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
          <CardFooter className="flex items-center justify-end text-sm text-gray-400 bg-gray-800 border-t border-gray-700">
            {formattedLastUpdated ? <span className="text-gray-400">Last updated {formattedLastUpdated}</span> : null}
          </CardFooter>
        </Card>
      </main>

      <footer className="border-t bg-gray-900/80 border-gray-700">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-6 text-sm text-gray-400 sm:flex-row sm:items-center sm:justify-between">
          <span>Data courtesy of CT Scraper Service</span>
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
            {formattedLastUpdated ? <span className="text-gray-400">Last updated {formattedLastUpdated}</span> : null}
            <a
              href="https://geoleads.land"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-gray-400 transition-colors hover:text-white"
            >
              geoleads.land
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}









































