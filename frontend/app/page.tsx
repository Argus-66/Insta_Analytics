'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const [username, setUsername] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;
    
    setIsLoading(true);
    try {
      // Navigate to profile page with the username
      router.push(`/profile/${username.trim().replace('@', '')}`);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-r from-black via-purple-900/30 to-black relative">
      {/* Street light effect */}
      <div className="absolute inset-0 bg-gradient-radial from-purple-500/20 via-transparent to-transparent opacity-60"></div>
      {/* Header */}
      <header className="px-6 py-4 relative z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">IA</span>
            </div>
            <span className="text-white text-xl font-semibold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
              Influencer Analytics
            </span>
          </div>
          <nav className="hidden md:flex space-x-8">
            <a href="#" className="text-white hover:text-purple-300 transition-colors">Search</a>
            <a href="#" className="text-white hover:text-purple-300 transition-colors">Trending</a>
            <a href="#" className="text-white hover:text-purple-300 transition-colors">Analytics</a>
            <a href="#" className="text-white hover:text-purple-300 transition-colors">About</a>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex flex-col items-center justify-center min-h-[80vh] px-6 relative z-10">
        <div className="text-center max-w-4xl mx-auto">
          {/* Hero Title */}
          <h1 className="text-6xl md:text-8xl font-bold mb-6">
            <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Discover
            </span>
            <br />
            <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              Influencers
            </span>
          </h1>
          
          {/* Subtitle */}
          <p className="text-xl text-gray-300 mb-12 max-w-2xl mx-auto leading-relaxed">
            Search and analyze Instagram influencer profiles with detailed insights, 
            engagement metrics, and comprehensive audience analytics
          </p>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="max-w-2xl mx-auto mb-12">
            <div className="relative">
              <div className="flex items-center bg-white/10 backdrop-blur-sm rounded-full p-2 border border-white/20">
                <div className="flex items-center px-4">
                  <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                    <span className="text-white text-xs font-bold">@</span>
                  </div>
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="@sarahjohnson_official"
                  className="flex-1 bg-transparent text-white placeholder-gray-400 text-lg py-4 px-4 focus:outline-none"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={isLoading || !username.trim()}
                  className="bg-gradient-to-r from-purple-500 to-blue-500 text-white px-8 py-4 rounded-full font-semibold hover:from-purple-600 hover:to-blue-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>
          </form>

          {/* Category Filters */}
          <div className="flex flex-wrap justify-center gap-3 mb-16">
            <button className="bg-gradient-to-r from-purple-500 to-blue-500 text-white px-6 py-3 rounded-full font-medium">
              All Categories
            </button>
            <button className="bg-white/10 backdrop-blur-sm text-white px-6 py-3 rounded-full font-medium hover:bg-white/20 transition-colors">
              Fashion
            </button>
            <button className="bg-white/10 backdrop-blur-sm text-white px-6 py-3 rounded-full font-medium hover:bg-white/20 transition-colors">
              Food & Lifestyle
            </button>
            <button className="bg-white/10 backdrop-blur-sm text-white px-6 py-3 rounded-full font-medium hover:bg-white/20 transition-colors">
              Tech
            </button>
            <button className="bg-white/10 backdrop-blur-sm text-white px-6 py-3 rounded-full font-medium hover:bg-white/20 transition-colors">
              Fitness
            </button>
            <button className="bg-white/10 backdrop-blur-sm text-white px-6 py-3 rounded-full font-medium hover:bg-white/20 transition-colors">
              Travel
            </button>
            <button className="bg-white/10 backdrop-blur-sm text-white px-6 py-3 rounded-full font-medium hover:bg-white/20 transition-colors">
              Beauty
            </button>
          </div>
        </div>

        {/* Trending Section */}
        <div className="w-full max-w-7xl mx-auto">
          <div className="flex items-center mb-8">
            <div className="w-1 h-8 bg-gradient-to-b from-purple-500 to-blue-500 rounded-full mr-4"></div>
            <h2 className="text-3xl font-bold text-white">Trending Influencers</h2>
          </div>
          
          {/* Placeholder for trending influencers */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10">
                <div className="flex items-center space-x-4 mb-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full"></div>
                  <div>
                    <div className="text-white font-semibold">@influencer{i}</div>
                    <div className="text-gray-400 text-sm">1.2M followers</div>
                  </div>
                </div>
                <div className="text-gray-300 text-sm">
                  Sample influencer profile data will appear here...
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
