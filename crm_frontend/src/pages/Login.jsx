import { useAuth0 } from '@auth0/auth0-react';
import { ShieldCheck, CarFront } from 'lucide-react';

export default function Login() {
  const { loginWithRedirect, isLoading } = useAuth0();

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <CarFront className="mx-auto h-16 w-16 text-blue-500" />
        <h2 className="mt-6 text-3xl font-extrabold text-white">
          Dealership CRM
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Agent Workspace & AI Handoff Portal
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-800 py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-slate-700">
          <button
            onClick={() => loginWithRedirect()}
            disabled={isLoading}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:ring-offset-slate-900 transition-colors disabled:opacity-50"
          >
            <ShieldCheck className="w-5 h-5 mr-2" />
            {isLoading ? 'Connecting to SSO...' : 'Agent Login (SSO)'}
          </button>
        </div>
      </div>
    </div>
  );
}