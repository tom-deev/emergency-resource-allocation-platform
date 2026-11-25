import { useCallback, useEffect, useState } from "react";
import "./App.css";
import {
  api,
  API_BASE_URL,
  clearSession,
  getStoredToken,
  getStoredUser,
} from "./api/client";
import AuthPage from "./components/AuthPage";
import DashboardView from "./components/DashboardView";
import PriorityQueueView from "./components/PriorityQueueView";
import IncidentsView from "./components/IncidentsView";
import CoordinationView from "./components/CoordinationView";
import AmbulancesView from "./components/AmbulancesView";
import HospitalsView from "./components/HospitalsView";
import ArchivedIncidentsView from "./components/ArchivedIncidentsView";

const PAGE_TITLES = {
  dashboard: {
    title: "Operations Dashboard",
    subtitle: "Live incident metrics, fleet availability, and hospital bed capacity",
  },
  queue: {
    title: "Incident Priority Queue",
    subtitle: "Deterministic severity ordering (P1–P4), IST timestamps, and waiting alerts",
  },
  incidents: {
    title: "Incident Management",
    subtitle: "Dispatchers report incidents; Resource Operators inspect, review, and verify",
  },
  coordination: {
    title: "Inspection & Resource Coordination",
    subtitle: "Resource Operator verification, ambulance dispatch, hospital admission, and completion",
  },
  ambulances: {
    title: "Ambulance Fleet",
    subtitle: "Manage ambulance registration, availability, and onboard equipment",
  },
  hospitals: {
    title: "Hospital Directory",
    subtitle: "Manage hospital registration, bed capacity, and medical facilities",
  },
  archived: {
    title: "Archived Incidents",
    subtitle: "Preserved completed incident records, timestamps, and hospital reservation history",
  },
};

export default function App() {
  const [user, setUser] = useState(() =>
    getStoredToken() ? getStoredUser() : null
  );
  const [activeTab, setActiveTab] = useState(() => {
    const stored = getStoredToken() ? getStoredUser() : null;
    return stored?.role === "DISPATCHER" ? "incidents" : "dashboard";
  });
  const [coordIncidentId, setCoordIncidentId] = useState("");

  const [incidents, setIncidents] = useState([]);
  const [archivedIncidents, setArchivedIncidents] = useState([]);
  const [ambulances, setAmbulances] = useState([]);
  const [hospitals, setHospitals] = useState([]);
  const [dashboardSummary, setDashboardSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [globalError, setGlobalError] = useState("");

  const isOperator = user?.role === "RESOURCE_OPERATOR";

  const refreshData = useCallback(async () => {
    if (!getStoredToken() || !user) return;
    setLoading(true);
    setGlobalError("");
    try {
      if (user.role === "DISPATCHER") {
        const incData = await api.getIncidents();
        setIncidents(Array.isArray(incData) ? incData : []);
        setArchivedIncidents([]);
        setAmbulances([]);
        setHospitals([]);
        setDashboardSummary(null);
      } else {
        const [incData, archivedData, ambData, hospData, summaryData] =
          await Promise.all([
            api.getIncidents(),
            api.getArchivedIncidents(),
            api.getAmbulances(),
            api.getHospitals(),
            api.getDashboardSummary(),
          ]);
        setIncidents(Array.isArray(incData) ? incData : []);
        setArchivedIncidents(Array.isArray(archivedData) ? archivedData : []);
        setAmbulances(Array.isArray(ambData) ? ambData : []);
        setHospitals(Array.isArray(hospData) ? hospData : []);
        setDashboardSummary(summaryData || null);
      }
    } catch (err) {
      if (err.status === 401) {
        clearSession();
        setUser(null);
        return;
      }
      setGlobalError(err.message || "Failed to load data from backend API.");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!user || !getStoredToken()) return;
    let cancelled = false;

    async function loadInitial() {
      try {
        if (user.role === "DISPATCHER") {
          const incData = await api.getIncidents();
          if (cancelled) return;
          setIncidents(Array.isArray(incData) ? incData : []);
          setArchivedIncidents([]);
          setAmbulances([]);
          setHospitals([]);
          setDashboardSummary(null);
          setGlobalError("");
        } else {
          const [incData, archivedData, ambData, hospData, summaryData] =
            await Promise.all([
              api.getIncidents(),
              api.getArchivedIncidents(),
              api.getAmbulances(),
              api.getHospitals(),
              api.getDashboardSummary(),
            ]);
          if (cancelled) return;
          setIncidents(Array.isArray(incData) ? incData : []);
          setArchivedIncidents(Array.isArray(archivedData) ? archivedData : []);
          setAmbulances(Array.isArray(ambData) ? ambData : []);
          setHospitals(Array.isArray(hospData) ? hospData : []);
          setDashboardSummary(summaryData || null);
          setGlobalError("");
        }
      } catch (err) {
        if (cancelled) return;
        if (err.status === 401) {
          clearSession();
          setUser(null);
          return;
        }
        setGlobalError(err.message || "Failed to load data from backend API.");
      }
    }

    loadInitial();
    return () => {
      cancelled = true;
    };
  }, [user]);

  function handleAuthenticated(loggedInUser) {
    setUser(loggedInUser);
    setActiveTab(loggedInUser?.role === "DISPATCHER" ? "incidents" : "dashboard");
  }

  function handleLogout() {
    clearSession();
    setUser(null);
    setIncidents([]);
    setAmbulances([]);
    setHospitals([]);
    setDashboardSummary(null);
    setActiveTab("dashboard");
  }

  function handleSelectForCoordination(incidentId) {
    if (!isOperator) return;
    setCoordIncidentId(incidentId);
    setActiveTab("coordination");
  }

  if (!user) {
    return <AuthPage onAuthenticated={handleAuthenticated} />;
  }

  const pendingRequestsCount = incidents.filter(
    (i) => i.status === "HOSPITAL_REQUESTED"
  ).length;
  const effectiveTab = isOperator ? activeTab : "incidents";
  const pageMeta =
    !isOperator
      ? {
          title: "My Reported Incidents",
          subtitle: "Report emergency incidents and track the status of your own submissions",
        }
      : PAGE_TITLES[effectiveTab] || PAGE_TITLES.dashboard;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>ERAP Control Center</h1>
          <span>Academic Minor Prototype</span>
        </div>

        <nav className="sidebar-nav">
          {isOperator ? (
            <>
              <button
                type="button"
                className={`nav-item ${effectiveTab === "dashboard" ? "active" : ""}`}
                onClick={() => setActiveTab("dashboard")}
              >
                <span>Dashboard</span>
              </button>

              <button
                type="button"
                className={`nav-item ${effectiveTab === "queue" ? "active" : ""}`}
                onClick={() => setActiveTab("queue")}
              >
                <span>Priority Queue</span>
                <span className="nav-count">{incidents.length}</span>
              </button>

              <button
                type="button"
                className={`nav-item ${effectiveTab === "incidents" ? "active" : ""}`}
                onClick={() => setActiveTab("incidents")}
              >
                <span>Incidents</span>
                <span className="nav-count">{incidents.length}</span>
              </button>

              <button
                type="button"
                className={`nav-item ${effectiveTab === "coordination" ? "active" : ""}`}
                onClick={() => setActiveTab("coordination")}
              >
                <span>Resource Coordination</span>
                {pendingRequestsCount > 0 && (
                  <span className="nav-count">{pendingRequestsCount}</span>
                )}
              </button>

              <button
                type="button"
                className={`nav-item ${effectiveTab === "ambulances" ? "active" : ""}`}
                onClick={() => setActiveTab("ambulances")}
              >
                <span>Ambulances</span>
                <span className="nav-count">{ambulances.length}</span>
              </button>

              <button
                type="button"
                className={`nav-item ${effectiveTab === "hospitals" ? "active" : ""}`}
                onClick={() => setActiveTab("hospitals")}
              >
                <span>Hospitals</span>
                <span className="nav-count">{hospitals.length}</span>
              </button>

              <button
                type="button"
                className={`nav-item ${effectiveTab === "archived" ? "active" : ""}`}
                onClick={() => setActiveTab("archived")}
              >
                <span>Archived Incidents</span>
                <span className="nav-count">{archivedIncidents.length}</span>
              </button>
            </>
          ) : (
            <button
              type="button"
              className="nav-item active"
              onClick={() => setActiveTab("incidents")}
            >
              <span>My Reported Incidents</span>
              <span className="nav-count">{incidents.length}</span>
            </button>
          )}
        </nav>

        <div className="sidebar-footer">
          <div>API: {API_BASE_URL}</div>
          <div style={{ marginTop: "4px" }}>Prototype Simulation Only</div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-title">
            <h2>{pageMeta.title}</h2>
            <p>{pageMeta.subtitle}</p>
          </div>

          <div className="topbar-actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={refreshData}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
            <div className="user-pill">
              <strong>{user.username}</strong>
              <span className="role-tag">{user.role}</span>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleLogout}
            >
              Sign Out
            </button>
          </div>
        </header>

        <main className="content">
          {globalError && <div className="alert alert-error">{globalError}</div>}

          {isOperator && effectiveTab === "dashboard" && (
            <DashboardView
              incidents={incidents}
              ambulances={ambulances}
              hospitals={hospitals}
              summary={dashboardSummary}
              onNavigate={setActiveTab}
            />
          )}

          {isOperator && effectiveTab === "queue" && (
            <PriorityQueueView
              onInspectIncident={handleSelectForCoordination}
            />
          )}

          {effectiveTab === "incidents" && (
            <IncidentsView
              user={user}
              incidents={incidents}
              onRefresh={refreshData}
              onSelectForCoordination={handleSelectForCoordination}
            />
          )}

          {isOperator && effectiveTab === "coordination" && (
            <CoordinationView
              user={user}
              incidents={incidents}
              ambulances={ambulances}
              hospitals={hospitals}
              initialIncidentId={coordIncidentId}
              onRefresh={refreshData}
            />
          )}

          {isOperator && effectiveTab === "ambulances" && (
            <AmbulancesView
              user={user}
              ambulances={ambulances}
              onRefresh={refreshData}
            />
          )}

          {isOperator && effectiveTab === "hospitals" && (
            <HospitalsView
              user={user}
              hospitals={hospitals}
              onRefresh={refreshData}
            />
          )}

          {isOperator && effectiveTab === "archived" && (
            <ArchivedIncidentsView archivedIncidents={archivedIncidents} />
          )}
        </main>
      </div>
    </div>
  );
}
