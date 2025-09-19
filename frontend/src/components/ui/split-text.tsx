import { useEffect, useRef } from "react";

export function SplitText({
  text,
  className = "",
}: {
  text: string;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const elements = ref.current?.querySelectorAll("span");
    if (elements) {
      elements.forEach((el, index) => {
        el.style.animationDelay = `${index * 0.05}s`;
      });
    }
  }, [text]);

  return (
    <div ref={ref} className={className}>
      {text.split("").map((char, index) => (
        <span
          key={index}
          className="inline-block opacity-0 animate-[slide-in_0.6s_ease-out_forwards]"
          style={{ animationDelay: `${index * 0.05}s` }}
        >
          {char === " " ? "\u00A0" : char}
        </span>
      ))}
    </div>
  );
}