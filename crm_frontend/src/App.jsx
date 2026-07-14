import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';
import { useAuthStore } from './store/authStore';
import Login from './pages/Login';

export default function App() {
  const { isAuthenticated, isLoading, getAccessTokenSilently } = useAuth0();
  const { setAuth, agent } = useAuthStore();
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const syncAgentProfile = async () => {
      if (isAuthenticated) {
        try {
            const token = await getAccessTokenSilently({
            authorizationParams: {
            audience: import.meta.env.VITE_AUTH0_AUDIENCE
            }
            });
          const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/auth/me`, {
            headers: {
              Authorization: `Bearer ${token}`
            }
          });
          setAuth(response.data, token);
        } catch (error) {
          console.error("Failed to sync agent profile with CRM API", error);
        }
      }
      setIsInitializing(false);
    };

    if (!isLoading) {
      syncAgentProfile();
    }
  }, [isAuthenticated, isLoading, getAccessTokenSilently, setAuth]);

  if (isLoading || (isAuthenticated && isInitializing)) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <Routes>
      {/* If the agent is authenticated and loaded into Zustand, go to Dashboard. Else, force Login */}
      <Route 
        path="/" 
        element={agent ? <Navigate to="/dashboard" /> : <Login />} 
      />
      
      {/* Placeholder for the actual Dashboard */}
      <Route 
        path="/dashboard" 
        element={
          agent ? (
            <div className="p-10 text-white bg-slate-900 min-h-screen">
              <h1 className="text-3xl font-bold mb-4">Welcome, {agent.name}!</h1>
              <p className="text-slate-400">Agent ID: {agent.agent_id}</p>
              <p className="text-slate-400">Role: {agent.role}</p>
            </div>
          ) : (
            <Navigate to="/" />
          )
        } 
      />
    </Routes>
  );
}