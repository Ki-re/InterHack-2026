import { useEffect, useRef, type ReactNode } from "react";

type HeroProps = {
  trustBadge?: {
    text: string;
    icons?: string[];
  };
  headline: {
    line1: string;
    line2: string;
  };
  subtitle: string;
  buttons?: {
    primary?: {
      text: string;
      onClick?: () => void;
    };
    secondary?: {
      text: string;
      onClick?: () => void;
    };
  };
  children?: ReactNode;
  className?: string;
};

type ProgramUniforms = {
  resolution: WebGLUniformLocation | null;
  time: WebGLUniformLocation | null;
  move: WebGLUniformLocation | null;
  touch: WebGLUniformLocation | null;
  pointerCount: WebGLUniformLocation | null;
  pointers: WebGLUniformLocation | null;
};

class WebGLRenderer {
  private canvas: HTMLCanvasElement;
  private gl: WebGL2RenderingContext;
  private program: WebGLProgram | null = null;
  private vs: WebGLShader | null = null;
  private fs: WebGLShader | null = null;
  private buffer: WebGLBuffer | null = null;
  private uniforms: ProgramUniforms | null = null;
  private shaderSource = defaultShaderSource;
  private mouseMove = [0, 0];
  private mouseCoords = [0, 0];
  private pointerCoords = [0, 0];
  private nbrOfPointers = 0;

  private vertexSrc = `#version 300 es
precision highp float;
in vec4 position;
void main(){gl_Position=position;}`;

  private vertices = [-1, 1, -1, -1, 1, 1, 1, -1];

  constructor(canvas: HTMLCanvasElement, gl: WebGL2RenderingContext) {
    this.canvas = canvas;
    this.gl = gl;
    this.gl.viewport(0, 0, canvas.width, canvas.height);
  }

  updateShader(source: string) {
    this.reset();
    this.shaderSource = source;
    this.setup();
    this.init();
  }

  updateMove(deltas: number[]) {
    this.mouseMove = deltas;
  }

  updateMouse(coords: number[]) {
    this.mouseCoords = coords;
  }

  updatePointerCoords(coords: number[]) {
    this.pointerCoords = coords;
  }

  updatePointerCount(nbr: number) {
    this.nbrOfPointers = nbr;
  }

  updateViewport() {
    this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
  }

  compile(shader: WebGLShader, source: string) {
    const gl = this.gl;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error("Shader compilation error:", gl.getShaderInfoLog(shader));
    }
  }

  test(source: string) {
    let result = null;
    const gl = this.gl;
    const shader = gl.createShader(gl.FRAGMENT_SHADER);
    if (!shader) {
      return "Could not create fragment shader.";
    }

    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      result = gl.getShaderInfoLog(shader);
    }
    gl.deleteShader(shader);
    return result;
  }

  reset() {
    const gl = this.gl;
    if (this.program && !gl.getProgramParameter(this.program, gl.DELETE_STATUS)) {
      if (this.vs) {
        gl.detachShader(this.program, this.vs);
        gl.deleteShader(this.vs);
      }
      if (this.fs) {
        gl.detachShader(this.program, this.fs);
        gl.deleteShader(this.fs);
      }
      gl.deleteProgram(this.program);
    }

    if (this.buffer) {
      gl.deleteBuffer(this.buffer);
    }

    this.program = null;
    this.vs = null;
    this.fs = null;
    this.buffer = null;
    this.uniforms = null;
  }

  setup() {
    const gl = this.gl;
    this.vs = gl.createShader(gl.VERTEX_SHADER);
    this.fs = gl.createShader(gl.FRAGMENT_SHADER);

    if (!this.vs || !this.fs) {
      console.error("Could not create shader.");
      return;
    }

    this.compile(this.vs, this.vertexSrc);
    this.compile(this.fs, this.shaderSource);
    this.program = gl.createProgram();

    if (!this.program) {
      console.error("Could not create shader program.");
      return;
    }

    gl.attachShader(this.program, this.vs);
    gl.attachShader(this.program, this.fs);
    gl.linkProgram(this.program);

    if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) {
      console.error(gl.getProgramInfoLog(this.program));
    }
  }

  init() {
    const gl = this.gl;
    const program = this.program;
    if (!program) return;

    this.buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(this.vertices), gl.STATIC_DRAW);

    const position = gl.getAttribLocation(program, "position");
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

    this.uniforms = {
      resolution: gl.getUniformLocation(program, "resolution"),
      time: gl.getUniformLocation(program, "time"),
      move: gl.getUniformLocation(program, "move"),
      touch: gl.getUniformLocation(program, "touch"),
      pointerCount: gl.getUniformLocation(program, "pointerCount"),
      pointers: gl.getUniformLocation(program, "pointers"),
    };
  }

  render(now = 0) {
    const gl = this.gl;
    const program = this.program;

    if (!program || !this.uniforms || gl.getProgramParameter(program, gl.DELETE_STATUS)) return;

    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);

    gl.uniform2f(this.uniforms.resolution, this.canvas.width, this.canvas.height);
    gl.uniform1f(this.uniforms.time, now * 1e-3);
    gl.uniform2f(this.uniforms.move, this.mouseMove[0], this.mouseMove[1]);
    gl.uniform2f(this.uniforms.touch, this.mouseCoords[0], this.mouseCoords[1]);
    gl.uniform1i(this.uniforms.pointerCount, this.nbrOfPointers);
    gl.uniform2fv(this.uniforms.pointers, this.pointerCoords);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
}

class PointerHandler {
  private active = false;
  private pointers = new Map<number, number[]>();
  private lastCoords = [0, 0];
  private moves = [0, 0];
  private element: HTMLCanvasElement;

  constructor(element: HTMLCanvasElement) {
    this.element = element;
    element.addEventListener("pointerdown", this.onPointerDown);
    element.addEventListener("pointerup", this.onPointerUp);
    element.addEventListener("pointerleave", this.onPointerUp);
    element.addEventListener("pointermove", this.onPointerMove);
  }

  destroy() {
    this.element.removeEventListener("pointerdown", this.onPointerDown);
    this.element.removeEventListener("pointerup", this.onPointerUp);
    this.element.removeEventListener("pointerleave", this.onPointerUp);
    this.element.removeEventListener("pointermove", this.onPointerMove);
  }

  get count() {
    return this.pointers.size;
  }

  get move() {
    return this.moves;
  }

  get coords() {
    return this.pointers.size > 0 ? Array.from(this.pointers.values()).flat() : [0, 0];
  }

  get first() {
    return this.pointers.values().next().value || this.lastCoords;
  }

  private mapPointer(e: PointerEvent) {
    const rect = this.element.getBoundingClientRect();
    const scaleX = this.element.width / rect.width;
    const scaleY = this.element.height / rect.height;
    return [(e.clientX - rect.left) * scaleX, this.element.height - (e.clientY - rect.top) * scaleY];
  }

  private onPointerDown = (e: PointerEvent) => {
    this.active = true;
    this.pointers.set(e.pointerId, this.mapPointer(e));
  };

  private onPointerUp = (e: PointerEvent) => {
    if (this.count === 1) {
      this.lastCoords = this.first;
    }
    this.pointers.delete(e.pointerId);
    this.active = this.pointers.size > 0;
  };

  private onPointerMove = (e: PointerEvent) => {
    if (!this.active) return;
    this.lastCoords = this.mapPointer(e);
    this.pointers.set(e.pointerId, this.lastCoords);
    this.moves = [this.moves[0] + e.movementX, this.moves[1] + e.movementY];
  };
}

function useShaderBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const rendererRef = useRef<WebGLRenderer | null>(null);
  const pointersRef = useRef<PointerHandler | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const gl = canvas.getContext("webgl2", { antialias: true });

    if (!gl) {
      return;
    }

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.max(1, 0.5 * window.devicePixelRatio);
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      rendererRef.current?.updateViewport();
    };

    const loop = (now: number) => {
      if (!rendererRef.current || !pointersRef.current) return;

      rendererRef.current.updateMouse(pointersRef.current.first);
      rendererRef.current.updatePointerCount(pointersRef.current.count);
      rendererRef.current.updatePointerCoords(pointersRef.current.coords);
      rendererRef.current.updateMove(pointersRef.current.move);
      rendererRef.current.render(now);
      animationFrameRef.current = requestAnimationFrame(loop);
    };

    rendererRef.current = new WebGLRenderer(canvas, gl);
    pointersRef.current = new PointerHandler(canvas);
    rendererRef.current.setup();
    rendererRef.current.init();
    resize();

    if (rendererRef.current.test(defaultShaderSource) === null) {
      rendererRef.current.updateShader(defaultShaderSource);
    }

    loop(0);
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      pointersRef.current?.destroy();
      rendererRef.current?.reset();
    };
  }, []);

  return canvasRef;
}

export default function Hero({
  trustBadge,
  headline,
  subtitle,
  buttons,
  children,
  className = "",
}: HeroProps) {
  const canvasRef = useShaderBackground();

  return (
    <div className={`relative h-screen w-full overflow-hidden bg-black ${className}`}>
      <style>{`
        @keyframes shader-hero-fade-in-down {
          from { opacity: 0; transform: translateY(-20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes shader-hero-fade-in-up {
          from { opacity: 0; transform: translateY(30px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .shader-hero-fade-in-down {
          animation: shader-hero-fade-in-down 0.8s ease-out forwards;
        }

        .shader-hero-fade-in-up {
          animation: shader-hero-fade-in-up 0.8s ease-out forwards;
          opacity: 0;
        }

        .shader-hero-delay-200 { animation-delay: 0.2s; }
        .shader-hero-delay-400 { animation-delay: 0.4s; }
        .shader-hero-delay-600 { animation-delay: 0.6s; }
        .shader-hero-delay-800 { animation-delay: 0.8s; }
      `}</style>

      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className="absolute inset-0 h-full w-full touch-none object-cover"
        style={{ background: "black" }}
      />

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,180,70,0.18),transparent_42%),linear-gradient(180deg,rgba(0,0,0,0.12),rgba(0,0,0,0.82))]" />

      <div className="absolute inset-0 z-10 flex flex-col items-center justify-center px-4 py-8 text-white">
        {trustBadge ? (
          <div className="mb-7 shader-hero-fade-in-down">
            <div className="flex items-center gap-2 rounded-full border border-orange-300/30 bg-orange-500/10 px-5 py-2.5 text-sm text-orange-100 shadow-lg shadow-orange-950/20 backdrop-blur-md">
              {trustBadge.icons?.length ? (
                <div className="flex gap-1 text-amber-300">
                  {trustBadge.icons.map((icon, index) => (
                    <span key={`${icon}-${index}`}>{icon}</span>
                  ))}
                </div>
              ) : null}
              <span>{trustBadge.text}</span>
            </div>
          </div>
        ) : null}

        <div className="mx-auto w-full max-w-5xl space-y-6 text-center">
          <div className="space-y-2">
            <h1 className="bg-gradient-to-r from-orange-300 via-yellow-400 to-amber-300 bg-clip-text text-5xl font-bold text-transparent shader-hero-fade-in-up shader-hero-delay-200 sm:text-6xl lg:text-8xl">
              {headline.line1}
            </h1>
            <h2 className="bg-gradient-to-r from-yellow-300 via-orange-400 to-red-400 bg-clip-text text-5xl font-bold text-transparent shader-hero-fade-in-up shader-hero-delay-400 sm:text-6xl lg:text-8xl">
              {headline.line2}
            </h2>
          </div>

          <p className="mx-auto max-w-3xl text-base font-light leading-7 text-orange-100/90 shader-hero-fade-in-up shader-hero-delay-600 sm:text-xl lg:text-2xl">
            {subtitle}
          </p>

          {buttons ? (
            <div className="mt-9 flex flex-col justify-center gap-3 shader-hero-fade-in-up shader-hero-delay-800 sm:flex-row">
              {buttons.primary ? (
                <button
                  className="inline-flex min-h-12 items-center justify-center rounded-full bg-gradient-to-r from-orange-500 to-yellow-500 px-8 py-3 text-base font-semibold text-black shadow-xl shadow-orange-500/25 transition-all duration-300 hover:scale-105 hover:from-orange-600 hover:to-yellow-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-200"
                  type="button"
                  onClick={buttons.primary.onClick}
                >
                  {buttons.primary.text}
                </button>
              ) : null}

              {buttons.secondary ? (
                <button
                  className="inline-flex min-h-12 items-center justify-center rounded-full border border-orange-300/30 bg-orange-500/10 px-8 py-3 text-base font-semibold text-orange-100 backdrop-blur-sm transition-all duration-300 hover:scale-105 hover:border-orange-300/50 hover:bg-orange-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-200"
                  type="button"
                  onClick={buttons.secondary.onClick}
                >
                  {buttons.secondary.text}
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {children ? <div className="absolute inset-0 z-20 pointer-events-none">{children}</div> : null}
    </div>
  );
}

const defaultShaderSource = `#version 300 es
/*********
* made by Matthias Hurrle (@atzedent)
*
*To explore strange new worlds, to seek out new life
*and new civilizations, to boldly go where no man has
*gone before.
*/
precision highp float;
out vec4 O;
uniform vec2 resolution;
uniform float time;
#define FC gl_FragCoord.xy
#define T time
#define R resolution
#define MN min(R.x,R.y)
float rnd(vec2 p) {
  p=fract(p*vec2(12.9898,78.233));
  p+=dot(p,p+34.56);
  return fract(p.x*p.y);
}
float noise(in vec2 p) {
  vec2 i=floor(p), f=fract(p), u=f*f*(3.-2.*f);
  float
  a=rnd(i),
  b=rnd(i+vec2(1,0)),
  c=rnd(i+vec2(0,1)),
  d=rnd(i+1.);
  return mix(mix(a,b,u.x),mix(c,d,u.x),u.y);
}
float fbm(vec2 p) {
  float t=.0, a=1.; mat2 m=mat2(1.,-.5,.2,1.2);
  for (int i=0; i<5; i++) {
    t+=a*noise(p);
    p*=2.*m;
    a*=.5;
  }
  return t;
}
float clouds(vec2 p) {
float d=1., t=.0;
for (float i=.0; i<3.; i++) {
float a=d*fbm(i*10.+p.x*.2+.2*(1.+i)*p.y+d+i*i+p);
t=mix(t,d,a);
d=a;
p*=2./(i+1.);
}
return t;
}
void main(void) {
vec2 uv=(FC-.5*R)/MN,st=uv*vec2(2,1);
vec3 col=vec3(0);
float bg=clouds(vec2(st.x+T*.5,-st.y));
uv*=1.-.3*(sin(T*.2)*.5+.5);
for (float i=1.; i<12.; i++) {
uv+=.1*cos(i*vec2(.1+.01*i, .8)+i*i+T*.5+.1*uv.x);
vec2 p=uv;
float d=length(p);
col+=.00125/d*(cos(sin(i)*vec3(1,2,3))+1.);
float b=noise(i+p+bg*1.731);
col+=.002*b/length(max(p,vec2(b*p.x*.02,p.y)));
col=mix(col,vec3(bg*.25,bg*.137,bg*.05),d);
}
O=vec4(col,1);
}`;
