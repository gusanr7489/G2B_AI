import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App as AntApp, ConfigProvider, Spin } from "antd";
import koKR from "antd/locale/ko_KR";

import LoginPage from "./pages/LoginPage";
import StaffDashboard from "./pages/StaffDashboard";
import ActiveProjects from "./pages/ActiveProjects";
import CompletedProjects from "./pages/CompletedProjects";
import CeoDashboard from "./pages/CeoDashboard";
import BidDetail from "./pages/BidDetail";
import AppShell from "./components/AppShell";
import { useAuth } from "./hooks/useAuth";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

function AdminOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Spin style={{ margin: "100px auto", display: "block" }} />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<StaffDashboard />} />
        <Route path="/projects/active" element={<ActiveProjects />} />
        <Route path="/projects/completed" element={<CompletedProjects />} />
        <Route path="/bids/:id" element={<BidDetail />} />
        <Route path="/ceo" element={<AdminOnly><CeoDashboard /></AdminOnly>} />
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={koKR}>
        <AntApp>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
