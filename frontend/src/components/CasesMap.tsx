import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { LatLngTuple } from "leaflet";
import L from "leaflet";

import type { CaseRecord } from "@/types";

const DEFAULT_CENTER: LatLngTuple = [41.6032, -73.0877];

function MapBounds({ positions }: { positions: LatLngTuple[] }) {
  const map = useMap();

  useEffect(() => {
    if (!positions.length) {
      map.setView(DEFAULT_CENTER, 8);
      return;
    }

    if (positions.length === 1) {
      map.setView(positions[0], 12);
      return;
    }

    const bounds = L.latLngBounds(positions);
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [map, positions]);

  return null;
}

function Boundaries() {
  const map = useMap();

  useEffect(() => {
    // State boundary
    fetch('https://gis.data.ct.gov/arcgis/rest/services/CTGov_Open_Data/Connecticut_State_Boundary/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson')
      .then(res => res.json())
      .then(data => {
        L.geoJSON(data, {
          style: {
            color: '#5227FF',
            weight: 3,
            opacity: 0.8,
            fillOpacity: 0.1
          }
        }).addTo(map);
      });

    // Counties
    fetch('https://gis.data.ct.gov/arcgis/rest/services/CTGov_Open_Data/Connecticut_Counties/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson')
      .then(res => res.json())
      .then(data => {
        L.geoJSON(data, {
          style: {
            color: '#4F20E8',
            weight: 2,
            opacity: 0.7,
            fillOpacity: 0
          }
        }).addTo(map);
      });

    // Towns (thinner lines to avoid clutter)
    fetch('https://gis.data.ct.gov/arcgis/rest/services/CTGov_Open_Data/Connecticut_Towns/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson')
      .then(res => res.json())
      .then(data => {
        L.geoJSON(data, {
          style: {
            color: '#A78BFA',
            weight: 1,
            opacity: 0.5,
            fillOpacity: 0
          }
        }).addTo(map);
      });

    // Clean up on unmount
    return () => {
      map.eachLayer(layer => {
        if (layer instanceof L.GeoJSON) {
          map.removeLayer(layer);
        }
      });
    };
  }, [map]);

  return null;
}

export interface CasesMapProps {
  cases: CaseRecord[];
}

export function CasesMap({ cases }: CasesMapProps) {
  const positions = useMemo(
    () =>
      cases
        .filter((row) => row.latitude != null && row.longitude != null)
        .map((row) => [row.latitude as number, row.longitude as number] as LatLngTuple),
    [cases]
  );

  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={8}
      scrollWheelZoom={false}
      className="relative z-0 h-[40vh] sm:h-[50vh] md:h-[60vh] w-full overflow-hidden rounded-lg border"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
      />
      <MapBounds positions={positions} />
      <Boundaries />
      {cases
        .filter((row) => row.latitude != null && row.longitude != null)
        .map((row, index) => {
          const center: LatLngTuple = [row.latitude as number, row.longitude as number];
          return (
            <CircleMarker
              key={`${row.docket_no ?? "case"}-${index}`}
              center={center}
              radius={6}
              pathOptions={{
                color: "#2563eb",
                weight: 1,
                fillColor: "#3b82f6",
                fillOpacity: 0.85,
              }}
            >
              <Popup maxWidth={260}>
                <div className="space-y-1 text-sm">
                  {row.docket_no ? <div className="font-semibold">{row.docket_no}</div> : null}
                  {row.town ? <div>{row.town}</div> : null}
                  {row.property_address ? <div>{row.property_address}</div> : null}
                  {row.county ? <div>{row.county} County</div> : null}
                  {row.case_type ? <div>{row.case_type}</div> : null}
                  {row.last_action_date ? <div>Last action: {row.last_action_date}</div> : null}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
    </MapContainer>
  );
}
