import React from 'react';

interface LogoLoopProps {}

const logos = [
  { name: 'airtable', alt: 'Airtable' },
  { name: 'stripe', alt: 'Stripe' },
  { name: 'openai', alt: 'OpenAI' },
  { name: 'gmail', alt: 'Gmail' },
  { name: 'youtube', alt: 'YouTube' },
  { name: 'github', alt: 'GitHub' },
];

const LogoLoop: React.FC<LogoLoopProps> = () => {
  return (
    <div className="overflow-hidden py-8 mt-8">
      <div className="flex animate-marquee whitespace-nowrap">
        {[...logos, ...logos].map((logo, index) => (
          <div key={index} className="flex-shrink-0 flex items-center justify-center mx-8 h-12">
            <img
              src={`https://cdn.simpleicons.org/${logo.name}/5227FF`}
              alt={logo.alt}
              className="h-8 w-auto opacity-80 hover:opacity-100 transition-opacity duration-300"
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default LogoLoop;