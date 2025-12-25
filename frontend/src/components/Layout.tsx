import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard' },
    { path: '/monitor', label: 'Monitor' },
    { path: '/settings', label: 'Settings' },
  ]

  return (
    <div className="min-h-screen bg-black">
      <nav className="bg-black border-b border-green-500/30 shadow-lg shadow-green-500/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-green-400 text-glow animate-pulse-glow">
                  ⚡ Binance Trading Console
                </h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                {navItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-all ${
                      location.pathname === item.path
                        ? 'border-green-500 text-green-400 text-glow'
                        : 'border-transparent text-green-600 hover:text-green-400 hover:border-green-500/50 hover-glow'
                    }`}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8 text-green-400">
        {children}
      </main>
    </div>
  )
}
