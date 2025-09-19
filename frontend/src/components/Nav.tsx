import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Nav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  return (
    <nav className="sticky top-0 z-50 relative bg-zinc-950/95 backdrop-blur-md border-b border-zinc-800/50 shadow-sm px-4 py-4">
      <div className="max-w-6xl mx-auto flex justify-between items-center">
        <Link to="/" className="text-xl font-bold text-white hover:scale-105 transition-transform duration-200">DocketVista</Link>
        <div className="hidden md:flex items-center space-x-6">
          <Link to="/" className="text-zinc-200 hover:text-white font-medium transition-colors duration-200">Home</Link>
          <Link to="/app" className="text-zinc-200 hover:text-white font-medium transition-colors duration-200">Dashboard</Link>
          <Link to="/pricing" className="text-zinc-200 hover:text-white font-medium transition-colors duration-200">Pricing</Link>
          <Link to="/about" className="text-zinc-200 hover:text-white font-medium transition-colors duration-200">About</Link>
          <Link to="/contact" className="text-zinc-200 hover:text-white font-medium transition-colors duration-200">Contact</Link>
          <Button variant="ghost" asChild className="ml-4 h-auto py-2 px-4 bg-[#5227FF]/10 border-[#5227FF]/30 hover:bg-[#5227FF]/20 transition-colors duration-200">
            <Link to="/login" className="text-zinc-200 hover:text-white font-medium transition-colors">Login</Link>
          </Button>
        </div>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden text-white p-1 hover:bg-zinc-800/50 rounded-md transition-colors duration-200"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-[999] bg-black/50 md:hidden"
            onClick={() => setMobileOpen(false)}
          />
          <div className="md:hidden fixed inset-x-0 top-16 z-[1000] bg-zinc-950 border-t border-zinc-700 shadow-2xl">
            <div className="px-4 py-4 space-y-4">
              <Link
                to="/"
                className="block text-zinc-200 hover:text-white font-medium transition-colors py-2"
                onClick={() => setMobileOpen(false)}
              >
                Home
              </Link>
              <Link
                to="/app"
                className="block text-zinc-200 hover:text-white font-medium transition-colors py-2"
                onClick={() => setMobileOpen(false)}
              >
                Dashboard
              </Link>
              <Link
                to="/pricing"
                className="block text-zinc-200 hover:text-white font-medium transition-colors py-2"
                onClick={() => setMobileOpen(false)}
              >
                Pricing
              </Link>
              <Link
                to="/about"
                className="block text-zinc-200 hover:text-white font-medium transition-colors py-2"
                onClick={() => setMobileOpen(false)}
              >
                About
              </Link>
              <Link
                to="/contact"
                className="block text-zinc-200 hover:text-white font-medium transition-colors py-2"
                onClick={() => setMobileOpen(false)}
              >
                Contact
              </Link>
              <Button asChild className="w-full justify-center">
                <Link
                  to="/login"
                  className="text-zinc-200 hover:text-white font-medium transition-colors"
                  onClick={() => setMobileOpen(false)}
                >
                  Login
                </Link>
              </Button>
            </div>
          </div>
        </>
      )}
    </nav>
  );
}