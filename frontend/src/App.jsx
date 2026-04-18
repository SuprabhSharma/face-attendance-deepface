import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import TrainerDashboard from "./pages/TrainerDashboard";
import StudentDashboard from "./pages/StudentDashboard";
import GroupManagement from "./pages/GroupManagement";
import AttendanceCamera from "./pages/AttendanceCamera";
import AttendanceReport from "./pages/AttendanceReport";
import FaceRegistration from "./pages/FaceRegistration";
import LoadingSpinner from "./components/LoadingSpinner";

function DashboardRouter() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return user.role === "trainer" ? <TrainerDashboard /> : <StudentDashboard />;
}

export default function App() {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <LoadingSpinner text="Loading…" />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Dashboard — role-based */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardRouter />
            </ProtectedRoute>
          }
        />

        {/* Trainer routes */}
        <Route
          path="/groups"
          element={
            <ProtectedRoute role="trainer">
              <GroupManagement />
            </ProtectedRoute>
          }
        />
        <Route
          path="/attendance"
          element={
            <ProtectedRoute role="trainer">
              <AttendanceCamera />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <ProtectedRoute role="trainer">
              <AttendanceReport />
            </ProtectedRoute>
          }
        />

        {/* Student routes */}
        <Route
          path="/register-face"
          element={
            <ProtectedRoute role="student">
              <FaceRegistration />
            </ProtectedRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
