'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Image from 'next/image';

interface ProfileData {
  username: string;
  full_name: string;
  profile_pic_url: string;
  followers_count: number;
  following_count: number;
  posts_count: number;
  recent_posts: Array<{
    image_url: string;
    caption: string;
    timestamp: string;
  }>;
  last_updated: string;
}

export default function ProfilePage() {
  const params = useParams();
  const username = params.username as string;
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        console.log(`🔍 Fetching profile for: ${username}`);
        
        // First try to get cached data (fastest)
        try {
          const cachedResponse = await fetch(`http://127.0.0.1:8000/api/profile/${username}/cached`);
          if (cachedResponse.ok) {
            const cachedData = await cachedResponse.json();
            
            // Check if cached data is useful (has followers or posts)
            const hasUsefulData = cachedData.followers_count > 0 || cachedData.posts_count > 0 || 
                                 (cachedData.recent_posts && cachedData.recent_posts.length > 0);
            
            if (hasUsefulData) {
              console.log(`⚡ Got useful cached data immediately`);
              setProfile(cachedData);
              setLoading(false);
              
              // Now fetch fresh data in background
              console.log(`🔄 Fetching fresh data in background...`);
              fetch(`http://127.0.0.1:8000/api/profile/${username}`)
                .then(response => response.json())
                .then(freshData => {
                  console.log(`🆕 Got fresh data, updating profile`);
                  setProfile(freshData);
                })
                .catch(err => {
                  console.log(`⚠️ Background refresh failed, keeping cached data: ${err.message}`);
                });
              return;
            } else {
              console.log(`📦 Cached data is empty, fetching fresh data`);
            }
          }
        } catch (err) {
          console.log(`📦 No cached data available, fetching fresh data`);
        }
        
        // If no cache, fetch fresh data
        const response = await fetch(`http://127.0.0.1:8000/api/profile/${username}`);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error(`❌ API Error: ${response.status} - ${errorText}`);
          throw new Error(`Profile not found: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`✅ Received fresh data:`, data);
        setProfile(data);
      } catch (err) {
        console.error('💥 Fetch error:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch profile');
      } finally {
        setLoading(false);
      }
    };

    if (username) {
      fetchProfile();
    }
  }, [username]);

  const formatNumber = (num: number | undefined | null) => {
    if (!num || num === 0) return '0';
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-r from-black via-purple-900/30 to-black relative flex items-center justify-center">
        <div className="absolute inset-0 bg-gradient-radial from-purple-500/20 via-transparent to-transparent opacity-60"></div>
        <div className="text-center relative z-10">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white text-xl">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-gradient-to-r from-black via-purple-900/30 to-black relative flex items-center justify-center">
        <div className="absolute inset-0 bg-gradient-radial from-purple-500/20 via-transparent to-transparent opacity-60"></div>
        <div className="text-center relative z-10">
          <h1 className="text-4xl font-bold text-white mb-4">Profile Not Found</h1>
          <p className="text-gray-300 mb-8">{error || 'The requested profile could not be found.'}</p>
          <a 
            href="/" 
            className="bg-gradient-to-r from-purple-500 to-blue-500 text-white px-6 py-3 rounded-full font-semibold hover:from-purple-600 hover:to-blue-600 transition-all duration-200"
          >
            Back to Search
          </a>
        </div>
      </div>
    );
  }

  // Check if profile has useful data
  const hasUsefulData = profile.followers_count > 0 || profile.posts_count > 0 || 
                       (profile.recent_posts && profile.recent_posts.length > 0);

  if (!hasUsefulData) {
    return (
      <div className="min-h-screen bg-gradient-to-r from-black via-purple-900/30 to-black relative flex items-center justify-center">
        <div className="absolute inset-0 bg-gradient-radial from-purple-500/20 via-transparent to-transparent opacity-60"></div>
        <div className="text-center relative z-10">
          <h1 className="text-4xl font-bold text-white mb-4">Profile Data Unavailable</h1>
          <p className="text-gray-300 mb-8">
            We couldn't retrieve data for @{profile.username}. This could be because:
            <br />• The profile is private
            <br />• Instagram is blocking our access
            <br />• The profile doesn't exist
          </p>
          <div className="space-y-4">
            <a 
              href="/" 
              className="bg-gradient-to-r from-purple-500 to-blue-500 text-white px-6 py-3 rounded-full font-semibold hover:from-purple-600 hover:to-blue-600 transition-all duration-200 mr-4"
            >
              Try Another Profile
            </a>
            <a 
              href="https://www.instagram.com/{profile.username}/" 
              target="_blank"
              rel="noopener noreferrer"
              className="bg-white/10 text-white px-6 py-3 rounded-full font-semibold hover:bg-white/20 transition-all duration-200"
            >
              View on Instagram
            </a>
          </div>
        </div>
      </div>
    );
  }

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
          <a 
            href="/" 
            className="text-white hover:text-purple-300 transition-colors"
          >
            ← Back to Search
          </a>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 relative z-10">
        {/* Profile Header */}
        <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/10 mb-8">
          <div className="flex flex-col md:flex-row items-center md:items-start space-y-6 md:space-y-0 md:space-x-8">
            {/* Profile Picture */}
            <div className="relative">
              {profile.profile_pic_url ? (
                <Image
                  src={profile.profile_pic_url}
                  alt={`${profile.username} profile`}
                  width={120}
                  height={120}
                  className="rounded-full border-4 border-gradient-to-r from-purple-500 to-blue-500"
                />
              ) : (
                <div className="w-[120px] h-[120px] bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-2xl font-bold">
                    {profile.username.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
            </div>

            {/* Profile Info */}
            <div className="flex-1 text-center md:text-left">
              <h1 className="text-4xl font-bold text-white mb-2">@{profile.username}</h1>
              <p className="text-xl text-gray-300 mb-6">{profile.full_name}</p>
              
              {/* Stats */}
              <div className="grid grid-cols-3 gap-6 max-w-md mx-auto md:mx-0">
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">{formatNumber(profile.followers_count)}</div>
                  <div className="text-gray-400">Followers</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">{formatNumber(profile.following_count)}</div>
                  <div className="text-gray-400">Following</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">{formatNumber(profile.posts_count)}</div>
                  <div className="text-gray-400">Posts</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Posts */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-white mb-6">Recent Posts</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {profile.recent_posts.map((post, index) => (
              <div key={index} className="bg-white/5 backdrop-blur-sm rounded-xl overflow-hidden border border-white/10 hover:bg-white/10 transition-all duration-200">
                <div className="relative aspect-square">
                  {post.image_url ? (
                    <Image
                      src={post.image_url}
                      alt={`Post ${index + 1}`}
                      fill
                      className="object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
                      <span className="text-white text-sm">No Image</span>
                    </div>
                  )}
                </div>
                <div className="p-4">
                  <p className="text-gray-300 text-sm line-clamp-3">
                    {post.caption.length > 150 
                      ? `${post.caption.substring(0, 150)}...` 
                      : post.caption
                    }
                  </p>
                  <p className="text-gray-500 text-xs mt-2">
                    {new Date(post.timestamp).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Last Updated */}
        <div className="text-center text-gray-400 text-sm">
          Last updated: {new Date(profile.last_updated).toLocaleString()}
        </div>
      </main>
    </div>
  );
}
