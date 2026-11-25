import { Link, Route, Routes } from "react-router";
import HomePage from "./pages/HomePage";
import ScanPage from "./pages/ScanPage";

// Every page of the app. Anything NOT starting with /api is React's (ADR 0005).
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/scan/:token" element={<ScanPage />} />
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
