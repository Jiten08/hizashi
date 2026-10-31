import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Console from "./pages/Console";
import Landing from "./pages/Landing";
import Owner from "./pages/Owner";
import Street from "./pages/Street";
import Street3D from "./pages/Street3D";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/h/:house" element={<Owner />} />
        <Route path="/street" element={<Street />} />
        <Route path="/street/3d" element={<Street3D />} />
        <Route path="/console" element={<Console />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
