import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Corrections from "./pages/Corrections";
import Dashboard from "./pages/Dashboard";
import Owners from "./pages/Owners";
import Rules from "./pages/Rules";
import SpecSheetDetail from "./pages/SpecSheetDetail";
import Upload from "./pages/Upload";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/spec-sheets/:id" element={<SpecSheetDetail />} />
        <Route path="/rules" element={<Rules />} />
        <Route path="/owners" element={<Owners />} />
        <Route path="/corrections" element={<Corrections />} />
      </Route>
    </Routes>
  );
}
