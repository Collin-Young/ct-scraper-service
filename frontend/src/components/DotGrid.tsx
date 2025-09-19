import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { gsap } from "gsap";
import { InertiaPlugin } from "gsap/InertiaPlugin";

import "./dot-grid.css";

gsap.registerPlugin(InertiaPlugin);

type Dot = {
  cx: number;
  cy: number;
  xOffset: number;
  yOffset: number;
  _inertiaApplied: boolean;
};

type PointerState = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  speed: number;
  lastTime: number;
  lastX: number;
  lastY: number;
};

type LetterDot = Dot & { animating: boolean };

type DotGridProps = {
  dotSize?: number;
  gap?: number;
  baseColor?: string;
  activeColor?: string;
  proximity?: number;
  speedTrigger?: number;
  shockRadius?: number;
  shockStrength?: number;
  maxSpeed?: number;
  resistance?: number;
  returnDuration?: number;
  className?: string;
  style?: React.CSSProperties;
};

function throttle<T extends (...args: any[]) => void>(fn: T, limit: number): T {
  let lastCall = 0;
  return function (this: unknown, ...args: Parameters<T>) {
    const now = performance.now();
    if (now - lastCall >= limit) {
      lastCall = now;
      fn.apply(this, args);
    }
  } as T;
}

type RGB = { r: number; g: number; b: number };

function hexToRgb(hex: string): RGB {
  const match = hex.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
  if (!match) return { r: 0, g: 0, b: 0 };
  return {
    r: parseInt(match[1], 16),
    g: parseInt(match[2], 16),
    b: parseInt(match[3], 16),
  };
}

export function DotGrid({
  dotSize = 16,
  gap = 20,
  baseColor = "#ffffff",
  activeColor = "#000000",
  proximity = 100,
  speedTrigger = 50,
  shockRadius = 50,
  shockStrength = 1,
  maxSpeed = 5,
  resistance = 0.95,
  returnDuration = 1,
  className = "",
  style,
}: DotGridProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dots, setDots] = useState<Dot[]>([]);
  const pointerState = useRef<PointerState>({
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    speed: 0,
    lastTime: 0,
    lastX: 0,
    lastY: 0,
  });
  const animationRefs = useRef<GSAPTimeline[]>([]);
  const dotRefs = useRef<(HTMLDivElement | null)[]>([]);

  const numCols = useMemo(() => Math.floor(window.innerWidth / (dotSize + gap)) + 1, [dotSize, gap]);
  const numRows = useMemo(() => Math.floor(window.innerHeight / (dotSize + gap)) + 1, [dotSize, gap]);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const newDots: Dot[] = [];

    for (let row = 0; row < numRows; row++) {
      for (let col = 0; col < numCols; col++) {
        const x = col * (dotSize + gap) + dotSize / 2;
        const y = row * (dotSize + gap) + dotSize / 2;
        newDots.push({
          cx: x,
          cy: y,
          xOffset: 0,
          yOffset: 0,
          _inertiaApplied: false,
        });
      }
    }

    setDots(newDots);

    animationRefs.current.forEach(tl => tl.kill());
    animationRefs.current = [];
    dotRefs.current = [];

    return () => {
      animationRefs.current.forEach(tl => tl.kill());
    };
  }, [numCols, numRows, dotSize, gap]);

  const updatePointer = useCallback(
    throttle((clientX: number, clientY: number, time: number) => {
      const { x, y, lastTime, lastX, lastY } = pointerState.current;
      const dt = time - lastTime;

      if (dt > 0) {
        pointerState.current.vx = (clientX - lastX) / dt * 1000;
        pointerState.current.vy = (clientY - lastY) / dt * 1000;
        pointerState.current.speed = Math.sqrt(pointerState.current.vx ** 2 + pointerState.current.vy ** 2);
      }

      pointerState.current.x = clientX;
      pointerState.current.y = clientY;
      pointerState.current.lastTime = time;
      pointerState.current.lastX = clientX;
      pointerState.current.lastY = clientY;
    }, 16),
    []
  );

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      updatePointer(e.clientX, e.clientY, performance.now());
    };

    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, [updatePointer]);

  useEffect(() => {
    const animateDots = () => {
      const { x, y, speed, vx, vy } = pointerState.current;

      dots.forEach((dot, index) => {
        const dx = dot.cx + dot.xOffset - x;
        const dy = dot.cy + dot.yOffset - y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const normalizedDist = Math.max(0, (proximity - dist) / proximity);

        if (dist < proximity) {
          const force = normalizedDist * shockStrength * Math.min(speed / speedTrigger, maxSpeed);
          dot.xOffset += (dx / dist) * force;
          dot.yOffset += (dy / dist) * force;

          dot._inertiaApplied = false;

          // Color interpolation
          const ref = dotRefs.current[index];
          if (ref) {
            const baseRgb = hexToRgb(baseColor);
            const activeRgb = hexToRgb(activeColor);
            const r = baseRgb.r + (activeRgb.r - baseRgb.r) * normalizedDist;
            const g = baseRgb.g + (activeRgb.g - baseRgb.g) * normalizedDist;
            const b = baseRgb.b + (activeRgb.b - baseRgb.b) * normalizedDist;
            gsap.to(ref, {
              backgroundColor: `rgb(${r}, ${g}, ${b})`,
              scale: 1 + normalizedDist,
              duration: 0.3,
              ease: "power2.out",
            });
          }
        } else if (!dot._inertiaApplied) {
          // Apply inertia
          dot.xOffset += vx * 0.001;
          dot.yOffset += vy * 0.001;
          dot._inertiaApplied = true;
        }

        // Apply resistance
        dot.xOffset *= resistance;
        dot.yOffset *= resistance;

        // Animate position
        const ref = dotRefs.current[index];
        if (ref) {
          gsap.to(ref, {
            x: dot.xOffset,
            y: dot.yOffset,
            duration: returnDuration,
            ease: "power2.out",
          });
        }
      });

      requestAnimationFrame(animateDots);
    };

    if (dots.length > 0) {
      animateDots();
    }
  }, [dots, proximity, shockStrength, speedTrigger, maxSpeed, resistance, returnDuration, baseColor, activeColor]);

  return (
    <div
      ref={containerRef}
      className={`dot-grid ${className}`}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        overflow: "hidden",
        ...style,
      }}
    >
      {dots.map((dot, index) => (
        <div
          key={index}
          ref={el => (dotRefs.current[index] = el)}
          className={`dot dot-${index}`}
          style={{
            position: "absolute",
            left: dot.cx - dotSize / 2,
            top: dot.cy - dotSize / 2,
            width: dotSize,
            height: dotSize,
            backgroundColor: baseColor,
            borderRadius: "50%",
            willChange: "transform, background-color",
          }}
        />
      ))}
    </div>
  );
}