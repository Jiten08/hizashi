import { Link } from "react-router-dom";

/** /street/3d — React Three Fiber street on the same store (N8). */
export default function Street3D() {
  return (
    <main className="mx-auto max-w-3xl p-6 text-center text-stone-500">
      <p>The 3D street comes in Phase 3 (N8).</p>
      <Link to="/street" className="mt-2 inline-block text-sun underline">Open the 2D street</Link>
    </main>
  );
}
