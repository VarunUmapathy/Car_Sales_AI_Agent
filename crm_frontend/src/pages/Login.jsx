import LeftBranding from '../components/layout/LeftBranding';
import AuthCard from '../components/layout/AuthCard';

export default function Login() {
  return (
    <div className="min-h-screen font-body flex overflow-x-hidden">
      <LeftBranding />
      <AuthCard />
    </div>
  );
}