import React, { useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import Nav from "../components/Nav";
import { Check, X } from "lucide-react";

export default function PricingSection() {
  const [billing, setBilling] = useState<"monthly" | "annual">("monthly");
  const isAnnual = billing === "annual";

  const plans = [
    {
      id: "county",
      name: "County Plan",
      coverage: "1 county",
      monthly: 69,
      annual: 690,
      popular: false,
      features: [
        "All core case types (foreclosures, evictions, probates, liens)",
        "Daily updates",
        "Email support"
      ],
      cta: "Choose Your County",
    },
    {
      id: "multi",
      name: "Multi-County Plan",
      coverage: "up to 4 counties",
      monthly: 249,
      annual: 2490,
      popular: false,
      features: [
        "All core case types",
        "Daily updates",
        "Priority support",
        "Custom alerts/filters"
      ],
      cta: "Select Counties",
    },
    {
      id: "statewide",
      name: "Statewide Plan",
      coverage: "all 8 Connecticut counties",
      monthly: 399,
      annual: 3990,
      popular: true,
      features: [
        "All case types",
        "Daily updates",
        "Priority support",
        "Bulk export/API ready"
      ],
      cta: "Get Statewide Access",
    },
  ];

  const fadeInUp = {
    initial: { opacity: 0, y: 20 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true },
  };

  const price = (id: string): number => {
    const prices = isAnnual ? { county: 690, multi: 2490, statewide: 3990 } : { county: 69, multi: 249, statewide: 399 };
    return prices[id as keyof typeof prices];
  };

  const period = isAnnual ? "yr" : "mo";
  const cta = (plan: typeof plans[0]): string => plan.cta;

  const features = [
    { name: "Coverage", county: "1 county", multi: "Up to 4 counties", statewide: "All 8 CT counties" },
    { name: "Case Types", county: "Core (foreclosures, evictions, probates, liens)", multi: "All core case types", statewide: "All case types" },
    { name: "Updates", county: "Daily", multi: "Daily", statewide: "Daily" },
    { name: "Support", county: "Email", multi: "Priority", statewide: "Priority" },
    { name: "Custom Alerts/Filters", county: "—", multi: "✓", statewide: "✓" },
    { name: "Bulk Export/API Ready", county: "—", multi: "—", statewide: "✓" },
  ];

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200">
      <Nav />

      {/* Hero */}
      <section className="py-8 sm:py-16 lg:py-20 max-w-6xl mx-auto px-2 sm:px-4 sm:px-6 lg:px-8">
        <motion.div {...fadeInUp} className="text-center">
          <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-4">Pricing Built for Investor ROI – Start Small, Scale Big</h1>
          <p className="text-lg sm:text-xl text-zinc-400 mb-8 max-w-2xl mx-auto">Unlock CT motivated seller leads with AI insights, starting at $69/month. Potential: $10k+ ROI from just one deal.</p>
          <div className="flex flex-wrap justify-center gap-2 sm:gap-4 mb-8">
            <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-medium bg-zinc-800 text-zinc-200 border border-zinc-700">7-Day Guarantee</span>
            <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-medium bg-zinc-800 text-zinc-200 border border-zinc-700">Cancel Anytime</span>
          </div>
          <div className="flex justify-center items-center gap-4 mb-8">
            <Button
              variant="outline"
              size="sm"
              className={`border-zinc-700 ${!isAnnual ? 'bg-zinc-800' : ''}`}
              onClick={() => setBilling("monthly")}
              aria-pressed={!isAnnual}
              aria-label="Bill monthly"
            >
              Monthly
            </Button>
            <Button
              variant="outline"
              size="sm"
              className={`border-zinc-700 ${isAnnual ? 'bg-zinc-800' : ''}`}
              onClick={() => setBilling("annual")}
              aria-pressed={isAnnual}
              aria-label="Bill annually (save 2 months)"
            >
              Annual (Save 2 months)
            </Button>
          </div>
        </motion.div>
      </section>

      {/* Plans */}
      <section className="py-12 sm:py-16 lg:py-20 max-w-6xl mx-auto px-2 sm:px-4 sm:px-6 lg:px-8">
        <motion.div {...fadeInUp} className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 md:gap-8">
          {plans.map((plan, index) => (
            <motion.div key={plan.id} {...fadeInUp} transition={{ delay: index * 0.1 }}>
              <Card className={`bg-zinc-900/60 border border-zinc-800 rounded-2xl shadow-lg ${plan.popular ? 'ring-1 ring-indigo-500/40 relative' : ''}`}>
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-indigo-500 text-white px-4 py-1 rounded-full text-sm font-medium">Best Value</div>
                )}
                <CardHeader className="text-center">
                  <CardTitle className="text-xl sm:text-2xl font-bold">{plan.name}</CardTitle>
                  <p className="text-zinc-400 text-base sm:text-lg mb-4">{plan.coverage}</p>
                  <div className="flex flex-col items-center">
                    <div className="text-3xl sm:text-4xl font-bold text-white mb-1">${price(plan.id)}</div>
                    <div className="text-zinc-400 mb-6 text-sm sm:text-base">per {period} <span className="text-xs text-zinc-500">(billed {isAnnual ? 'annually' : 'monthly'})</span></div>
                    {isAnnual && <p className="text-xs text-zinc-500 mb-6">Billed annually · save 2 months</p>}
                    <ul className="space-y-2 text-left w-full">
                      {plan.features.map((feature) => (
                        <li key={feature} className="flex items-center text-zinc-300 text-sm">
                          <Check className="h-4 w-4 text-indigo-500 mr-2" /> {feature}
                        </li>
                      ))}
                    </ul>
                    <Button asChild className="w-full mt-6 bg-indigo-600 hover:bg-indigo-700" aria-label={`Get started with ${plan.name} plan`}>
                      <Link to="/signup">{cta(plan)}</Link>
                    </Button>
                  </div>
                </CardHeader>
              </Card>
            </motion.div>
          ))}
        </motion.div>
        <p className="text-center text-sm text-zinc-500 mt-8">Prices exclude taxes. Cancel anytime before renewal. <a href="/terms" className="text-indigo-400 hover:underline">Terms apply</a>.</p>
      </section>

      {/* Comparison Table */}
      <section className="py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.h2 {...fadeInUp} className="text-3xl font-bold text-center mb-12">Investor Features Comparison</motion.h2>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border border-zinc-700">
            <thead className="sticky top-0 bg-zinc-900/60 backdrop-blur-sm">
              <tr>
                <th scope="col" className="border border-zinc-700 p-4 text-left font-semibold">Features</th>
                {plans.map((plan) => (
                  <th key={plan.id} scope="col" className={`border border-zinc-700 p-4 text-center font-semibold ${plan.popular ? 'bg-indigo-500/10' : ''}`}>
                    {plan.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {features.map((feature) => (
                <tr key={feature.name} className="border border-zinc-700">
                  <th scope="row" className="border border-zinc-700 p-4 font-medium">{feature.name}</th>
                  {plans.map((plan) => {
                    const key = plan.id as keyof typeof feature;
                    const value = feature[key];
                    const Icon = value === '✓' ? Check : value === '—' ? X : null;
                    return (
                      <td key={plan.id} className="border border-zinc-700 p-4 text-center">
                        {Icon ? <Icon className={`mx-auto h-5 w-5 ${value === '✓' ? 'text-green-500' : 'text-zinc-500'}`} aria-hidden="true" /> : value}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 bg-zinc-900/20">
        <motion.h2 {...fadeInUp} className="text-3xl font-bold text-center mb-12">Investor Questions</motion.h2>
        <Accordion type="single" collapsible className="w-full max-w-2xl mx-auto">
          <AccordionItem value="billing">
            <AccordionTrigger>How does pricing drive ROI?</AccordionTrigger>
            <AccordionContent>County Plan ($69/mo) for targeted leads; Multi-County ($249/mo) for expanded coverage; Statewide ($399/mo) for full access and API integration.</AccordionContent>
          </AccordionItem>
          <AccordionItem value="limits">
            <AccordionTrigger>What if I need more counties?</AccordionTrigger>
            <AccordionContent>County Plan: 1 county; Multi-County: up to 4; Statewide: all 8 CT counties included.</AccordionContent>
          </AccordionItem>
          <AccordionItem value="coverage">
            <AccordionTrigger>Geography focus?</AccordionTrigger>
            <AccordionContent>Connecticut statewide coverage across all plans, with flexible county selection.</AccordionContent>
          </AccordionItem>
          <AccordionItem value="cancel">
            <AccordionTrigger>Guarantee details?</AccordionTrigger>
            <AccordionContent>7-day money-back, 99% accuracy. Cancel anytime, prorated annual.</AccordionContent>
          </AccordionItem>
        </Accordion>
      </section>

      {/* Bottom CTA */}
      <footer className="bg-indigo-600 py-8 sm:py-12 text-center">
        <motion.div {...fadeInUp}>
          <h2 className="text-2xl sm:text-3xl font-bold mb-4 text-white">Ready to Unlock Your Deal Flow?</h2>
          <p className="text-indigo-100 mb-6 text-base sm:text-lg">Select a plan for CT leads. Start closing smarter deals now.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="w-full sm:w-auto bg-white text-indigo-600 hover:bg-gray-100 px-4 sm:px-8">
              <Link to="/signup">Get Started</Link>
            </Button>
            <Button variant="outline" size="lg" className="w-full sm:w-auto border-white text-white hover:bg-white/10 px-4 sm:px-8" asChild>
              <Link to="/contact">Book Demo</Link>
            </Button>
          </div>
        </motion.div>
      </footer>
    </div>
  );
}