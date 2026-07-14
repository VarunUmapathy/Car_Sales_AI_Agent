import { CarFront, Star } from 'lucide-react';

export default function LeftBranding() {
  return (
    <aside className="hidden lg:flex w-1/2 relative flex-col justify-between p-16 bg-primary overflow-hidden">
      {/* Visual Background Pattern */}
      <div 
        className="absolute inset-0 opacity-20" 
        style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #ffffff 1px, transparent 0)', backgroundSize: '32px 32px' }}
      ></div>
      
      <div className="relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
            <CarFront className="text-primary w-6 h-6" />
          </div>
          <h1 className="font-headline text-3xl font-bold text-white tracking-tight">Dealership CRM</h1>
        </div>
      </div>

      <div className="relative z-10 max-w-md">
        <h2 className="font-headline text-4xl font-bold text-white mb-6">Drive growth with smarter relationships.</h2>
        <p className="text-white/80 font-body text-lg leading-relaxed">
          Connect your team, streamline your workflows, and unlock deep customer insights with the industry's most agile AI-driven platform.
        </p>
      </div>

      <div className="relative z-10">
        <div className="flex items-center gap-4 p-6 bg-primary-container/40 backdrop-blur-xl rounded-xl border border-white/10 w-max">
          <div className="flex -space-x-3">
            <img className="w-10 h-10 rounded-full border-2 border-primary object-cover" alt="User 1" src="https://i.pravatar.cc/100?img=47" />
            <img className="w-10 h-10 rounded-full border-2 border-primary object-cover" alt="User 2" src="https://i.pravatar.cc/100?img=11" />
            <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-primary font-bold border-2 border-primary text-xs">
              +12k
            </div>
          </div>
          <div className="text-white">
            <p className="font-body text-sm font-medium">Trusted by leading dealerships</p>
            <div className="flex text-yellow-400 mt-1">
              {[...Array(5)].map((_, i) => (
                <Star key={i} className="w-4 h-4 fill-current" />
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Decorative element */}
      <div className="absolute -bottom-20 -right-20 w-96 h-96 bg-blue-400/20 rounded-full blur-3xl"></div>
    </aside>
  );
}