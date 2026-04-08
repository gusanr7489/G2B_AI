import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App as AntApp, ConfigProvider } from "antd";
import koKR from "antd/locale/ko_KR";

import LoginPage from "./pages/LoginPage";
import StaffDashboard from "./pages/StaffDashboard";
import CeoDashboard from "./pages/CeoDashboard";
import BidDetail from "./pages/BidDetail";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={koKR}>
        <AntApp>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/dashboard" element={<StaffDashboard />} />
              <Route path="/ceo" element={<CeoDashboard />} />
              <Route path="/bids/:id" element={<BidDetail />} />
              <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
