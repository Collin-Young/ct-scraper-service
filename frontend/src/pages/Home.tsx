import { useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { DotGrid } from "@/components/DotGrid";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import RotatingText from "@/components/RotatingText";
import TextType from "@/components/TextType";
import Nav from "../components/Nav";
import LogoLoop from "../components/LogoLoop";

export default function Home() {
  const buttonRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/pricing'); // Redirect to pricing for sign-up flow
  };

  return (
    <div className="relative bg-gray-900">
      <Nav />
      <DotGrid
        dotSize={6}
        gap={50}
        baseColor="#F3F4F6"
        activeColor="#5227FF"
        proximity={150}
        shockStrength={1}
        resistance={0.98}
        returnDuration={0.5}
        className="z-0 opacity-10"
      />
      <div className="relative z-10 px-2 sm:px-4 pt-8 sm:pt-16 bg-gradient-to-b from-gray-900 via-purple-900/10 to-gray-900">
        {/* Hero Section */}
        <section className="flex items-start justify-center py-8 sm:py-16">
          <div className="text-center max-w-4xl mx-auto">
            <TextType
              text="AI-Powered Motivated Seller Leads: Start in Connecticut, Scale Nationally"
              as="h1"
              className="text-3xl sm:text-5xl md:text-7xl font-bold mb-6 tracking-tight"
              typingSpeed={50}
              initialDelay={500}
              showCursor={true}
              textColors={['#ffffff']}
            />
            <p className="text-lg sm:text-xl md:text-2xl text-gray-200 mb-8 leading-relaxed">
              Unlike raw lists from competitors, DocketVista uses advanced AI to analyze foreclosures, liens, evictions, and more—delivering actionable insights for smarter deals and higher ROI. Get fresh CT leads today and be first for nationwide expansion.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
              <Button
                onClick={handleGetStarted}
                size="lg"
                className="w-full sm:w-auto bg-[#5227FF] hover:bg-[#4F20E8] text-white px-4 sm:px-8 py-4 text-base sm:text-xl"
              >
                Start Free Trial - CT Counties Now
              </Button>
              <Button
                variant="outline"
                asChild
                size="lg"
                className="w-full sm:w-auto border-white/50 text-white px-4 sm:px-8 py-4 text-base sm:text-xl"
              >
                <Link to="/contact">Book a Demo</Link>
              </Button>
            </div>
            <p className="text-sm text-gray-400">Limited: Early Access Pricing for CT Launch – Expanding Soon to All States</p>
          </div>
        </section>
      
        {/* Value Section */}
        <section className="py-12 sm:py-20 max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Why DocketVista Beats Basic Lead Lists</h2>
            <p className="text-lg sm:text-xl text-gray-300">Unlike PropStream or PropertyRadar with stale data weeks or months behind, DocketVista delivers AI-driven analysis, broader coverage, daily refreshed leads, and customization for real estate investors like you.</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="bg-gray-800/50 border-white/20 text-white p-6">
              <CardContent className="pt-6">
                <h3 className="text-xl font-semibold mb-2">AI Insights, Not Just Names</h3>
                <p className="text-gray-300">Get prioritized leads with risk scores, property values, and deal potential—turn data into dollars faster.</p>
              </CardContent>
            </Card>
            <Card className="bg-gray-800/50 border-white/20 text-white p-6">
              <CardContent className="pt-6">
                <h3 className="text-xl font-semibold mb-2">Broader Coverage</h3>
                <p className="text-gray-300">Foreclosures, liens, evictions, divorces, and emerging cases. No gaps in your pipeline.</p>
              </CardContent>
            </Card>
            <Card className="bg-gray-800/50 border-white/20 text-white p-6">
              <CardContent className="pt-6">
                <h3 className="text-xl font-semibold mb-2">Custom Geography</h3>
                <p className="text-gray-300">Subscribe by CT county now; select multi-state filters as we roll out nationally. Exclusivity included.</p>
              </CardContent>
            </Card>
            <Card className="bg-gray-800/50 border-white/20 text-white p-6">
              <CardContent className="pt-6">
                <h3 className="text-xl font-semibold mb-2">Daily Delivery</h3>
                <p className="text-gray-300">Refreshed daily Mon-Fri at 4-5 PM EST—unlike competitors' outdated leads weeks or months old. 99% accurate, exclusive, ready to act on.</p>
              </CardContent>
            </Card>
          </div>
          <div className="text-center mt-12">
            <Button asChild size="lg">
              <Link to="/pricing">See Pricing Plans Tailored for Investors</Link>
            </Button>
          </div>
          <LogoLoop />
        </section>
      
        {/* How It Works Section */}
        <section className="py-16 sm:py-24 max-w-6xl mx-auto bg-gray-800/30 rounded-lg mb-16">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Get Leads in 3 Simple Steps</h2>
          </div>
          <div className="grid md:grid-cols-4 gap-4 sm:gap-8 items-center">
            <div className="text-center">
              <div className="w-16 h-16 bg-[#5227FF] rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white font-bold text-lg">1</span>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Sign Up & Select</h3>
              <p className="text-gray-300">Sign up and select your CT counties (or preview national options). Choose categories like foreclosures or evictions.</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-[#5227FF] rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white font-bold text-lg">2</span>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">AI Analyzes</h3>
              <p className="text-gray-300">Our AI scans legal dockets, analyzes data for insights (e.g., urgency scores, party details), and curates your list.</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-[#5227FF] rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white font-bold text-lg">3</span>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Receive Daily</h3>
              <p className="text-gray-300">Receive your customized leads daily via secure download. Market confidently with built-in exclusivity.</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-[#5227FF] rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white font-bold text-lg">4</span>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Scale Nationally</h3>
              <p className="text-gray-300">As we expand, customize multi-state views—stay ahead with early access alerts.</p>
            </div>
          </div>
          <div className="text-center mt-12">
            <Button onClick={handleGetStarted} size="lg" className="bg-[#5227FF] hover:bg-[#4F20E8]">
              Start Step 1: Free Trial
            </Button>
          </div>
        </section>
      
      
        {/* Final CTA Section */}
        <section className="py-12 sm:py-20 text-center bg-gray-800/30 rounded-lg max-w-4xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Ready to Boost Your Deal Flow?</h2>
          <p className="text-lg sm:text-xl text-gray-300 mb-8">Sign up now for CT leads + priority national access. No credit card needed.</p>
          <Button onClick={handleGetStarted} size="lg" className="w-full sm:w-auto bg-[#5227FF] hover:bg-[#4F20E8] text-base sm:text-xl px-8 sm:px-12 py-4 sm:py-6">
            Get Started Free
          </Button>
          <p className="text-sm text-gray-400 mt-4">Questions? <Link to="/contact" className="text-[#5227FF] hover:underline">Chat or Book Demo</Link></p>
        </section>
      </div>
    </div>
  );
}