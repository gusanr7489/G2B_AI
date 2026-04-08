import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App as AntApp, ConfigProvider, Spin } from "antd";
import koKR from "antd/locale/ko_KR";

import LoginPage from "./pages/LoginPage";
import StaffDashboard from "./pages/StaffDashboard";
import CeoDashboard from "./pages/CeoDashboard";
import BidDetail from "./pages/BidDetail";
import { useAuth } from "./hooks/useAuth";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

function RoleGuard({ role, children }: { role: "admin" | "staff"; children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) return <Spin style={{ margin: "100px auto", display: "block" }} />;
  if (!user) return <Navigate to="/login" replace />;
  if (role === "admin" && user.role !== "admin") return <Navigate to="/dashboard" replace />;
  if (role === "staff" && user.role === "admin") return <Navigate to="/ceo" replace />;
  return <>{children}</>;
}

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Spin style={{ margin: "100px auto", display: "block" }} />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={<RoleGuard role="staff"><StaffDashboard /></RoleGuard>} />
      <Route path="/ceo" element={<RoleGuard role="admin"><CeoDashboard /></RoleGuard>} />
      <Route path="/bids/:id" element={<AuthGuard><BidDetail /></AuthGuard>} />
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
