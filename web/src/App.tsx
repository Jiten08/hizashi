// Desktop demo only: the street dashboard and its controls. Owners use the phone app (mobile/).
import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "./components/ui";
import Console from "./pages/Console";
import Dashboard from "./pages/Dashboard";

// three.js only loads when someone opens the 3D street.
const Street3D = lazy(() => import("./pages/Street3D"));

export default function App() {
  return (
    <BrowserRouter>
      <Toaster />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/console" element={<Console />} />
        <Route path="/street/3d" element={<Suspense fallback={null}><Street3D /></Suspense>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
