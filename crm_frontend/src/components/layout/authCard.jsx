import { useAuth0 } from '@auth0/auth0-react';
import { CarFront, ArrowRight, ShieldCheck } from 'lucide-react';

export default function AuthCard() {
  const { loginWithRedirect, isLoading } = useAuth0();

  const handleLogin = () => {
    loginWithRedirect({
      authorizationParams: {
        audience: import.meta.env.VITE_AUTH0_AUDIENCE
      }
    });
  };

  return (
    <main className="w-full lg:w-1/2 flex items-center justify-center p-6 lg:p-12 bg-surface">
      <div className="w-full max-w-md">
        
        {/* Mobile Logo (Hidden on Desktop) */}
        <div className="lg:hidden flex justify-center mb-10">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <CarFront className="text-white w-5 h-5" />
            </div>
            <h1 className="font-headline text-2xl font-bold text-primary tracking-tight">Dealership CRM</h1>
          </div>
        </div>

        <div className="mb-10 text-center lg:text-left">
          <h2 className="font-headline text-3xl font-semibold text-on-surface mb-3">Welcome back</h2>
          <p className="text-on-surface-variant font-body text-base">
            Access your secure agent workspace and live inventory dashboard.
          </p>
        </div>

        <div className="bg-white p-8 rounded-xl border border-outline-variant shadow-sm mb-8">
          <div className="flex items-center justify-center mb-6 text-primary">
            <ShieldCheck className="w-12 h-12 opacity-80" />
          </div>
          
          <button 
            onClick={handleLogin}
            disabled={isLoading}
            className="w-full py-4 bg-primary hover:bg-blue-700 text-white font-body font-medium text-base rounded-lg shadow-sm hover:shadow-md active:scale-[0.98] transition-all flex items-center justify-center gap-2 group disabled:opacity-70"
          >
            {isLoading ? 'Connecting...' : 'Secure Agent Login (SSO)'}
            {!isLoading && <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />}
          </button>
        </div>

        <footer className="mt-12 text-center text-on-surface-variant font-body text-sm">
          <p>© {new Date().getFullYear()} Dealership CRM Inc. All rights reserved.</p>
          <div className="mt-2 space-x-4">
            <a href="#" className="hover:text-primary transition-colors">IT Help Center</a>
            <span>&middot;</span>
            <a href="#" className="hover:text-primary transition-colors">Agent Support</a>
          </div>
        </footer>

      </div>
    </main>
  );
}