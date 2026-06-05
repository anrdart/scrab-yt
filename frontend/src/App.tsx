import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Dashboard } from "./pages/Dashboard";
import { NewAnalysis } from "./pages/NewAnalysis";
import { AnalysisDetail } from "./pages/AnalysisDetail";
import { I18nProvider } from "./lib/i18n";

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(() => (typeof window === "undefined" ? true : window.innerWidth >= 768));

  useEffect(() => {
    const handleResize = () => setSidebarOpen(window.innerWidth >= 768);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <I18nProvider>
      <BrowserRouter>
        <div className="app-shell flex h-screen overflow-hidden">
          <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/analyses/new" element={<NewAnalysis />} />
              <Route path="/analyses/:id" element={<AnalysisDetail />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </I18nProvider>
  );
}

export default App;
