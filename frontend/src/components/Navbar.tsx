import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="bg-gray-900 text-white">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
        <Link href="/" className="font-bold text-lg tracking-tight">
          LCP
        </Link>
        <Link href="/" className="text-sm text-gray-300 hover:text-white">
          Home
        </Link>
      </div>
    </nav>
  );
}
