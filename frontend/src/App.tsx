import { Link, Route, Routes } from "react-router";
import AgendaPage from "./pages/AgendaPage";
import BoothLeadsPage from "./pages/BoothLeadsPage";
import HomePage from "./pages/HomePage";
import MyBoothsPage from "./pages/MyBoothsPage";
import ScanPage from "./pages/ScanPage";

// Every page of the app. Anything NOT starting with /api is React's (ADR 0005).
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/scan/:token" element={<ScanPage />} />
      <Route path="/events/:slug/agenda" element={<AgendaPage />} />
      <Route path="/my-booths" element={<MyBoothsPage />} />
      <Route path="/my-booths/:boothId" element={<BoothLeadsPage />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

function NotFound() {
  return (
    <main className="page">
      <h1>Page not found</h1>
      <Link className="button" to="/">Go home</Link>
    </main>
  );
}
