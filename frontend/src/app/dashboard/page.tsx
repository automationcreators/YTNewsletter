'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { PlaySquare, Users, Mail, TrendingUp, Plus, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { formatRelativeDate, formatNumber } from '@/lib/utils';
import type { VideoFeedItem, Subscription } from '@/lib/types';

export default function DashboardPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  const { data: subscriptions, isLoading: subsLoading } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: () => api.getSubscriptions(),
    enabled: isAuthenticated,
  });

  const { data: limit } = useQuery({
    queryKey: ['subscription-limit'],
    queryFn: () => api.getSubscriptionLimit(),
    enabled: isAuthenticated,
  });

  const { data: feed, isLoading: feedLoading } = useQuery({
    queryKey: ['video-feed', 7],
    queryFn: () => api.getVideoFeed(7, 1, 5),
    enabled: isAuthenticated,
  });

  const { data: newsletters } = useQuery({
    queryKey: ['newsletters'],
    queryFn: () => api.getNewsletters(1, 3),
    enabled: isAuthenticated,
  });

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const channelCount = subscriptions?.length || 0;
  const maxChannels = limit?.max_channels || user?.max_channels || 3;
  const recentVideos = feed?.items?.filter((v: VideoFeedItem) => v.has_summary).length || 0;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Welcome Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.display_name || 'there'}!
        </h1>
        <p className="text-gray-600 mt-1">
          Here&apos;s what&apos;s happening with your YouTube subscriptions.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Channels</p>
                <p className="text-2xl font-bold text-gray-900">
                  {channelCount}/{maxChannels}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-lg">
                <PlaySquare className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">New Videos (7d)</p>
                <p className="text-2xl font-bold text-gray-900">{feed?.total || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Summaries Ready</p>
                <p className="text-2xl font-bold text-gray-900">{recentVideos}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-100 rounded-lg">
                <Mail className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Newsletters</p>
                <p className="text-2xl font-bold text-gray-900">
                  {newsletters?.total || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Videos */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Videos</CardTitle>
            <Link href="/feed">
              <Button variant="ghost" size="sm">
                View all <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {feedLoading ? (
              <div className="p-6 text-center text-gray-500">Loading...</div>
            ) : feed?.items?.length > 0 ? (
              <div className="divide-y divide-gray-100">
                {feed.items.slice(0, 5).map((video: VideoFeedItem) => (
                  <Link
                    key={video.id}
                    href={`/feed/${video.id}`}
                    className="flex items-center gap-4 p-4 hover:bg-gray-50 transition-colors"
                  >
                    <img
                      src={video.thumbnail_url}
                      alt={video.title}
                      className="w-24 h-14 object-cover rounded"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {video.title}
                      </p>
                      <p className="text-xs text-gray-500">
                        {video.channel_name} &bull; {formatRelativeDate(video.published_at)}
                      </p>
                    </div>
                    {video.has_summary && (
                      <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded">
                        Summary
                      </span>
                    )}
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-gray-500">
                <p>No recent videos</p>
                <Link href="/channels">
                  <Button variant="outline" size="sm" className="mt-2">
                    <Plus className="w-4 h-4 mr-1" /> Add channels
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Subscribed Channels */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Your Channels</CardTitle>
            <Link href="/channels">
              <Button variant="ghost" size="sm">
                Manage <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {subsLoading ? (
              <div className="p-6 text-center text-gray-500">Loading...</div>
            ) : subscriptions?.length > 0 ? (
              <div className="divide-y divide-gray-100">
                {subscriptions.slice(0, 5).map((sub: Subscription) => (
                  <div
                    key={sub.id}
                    className="flex items-center gap-4 p-4"
                  >
                    <img
                      src={sub.channel.thumbnail_url}
                      alt={sub.channel.name}
                      className="w-10 h-10 rounded-full"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {sub.channel.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatNumber(sub.channel.subscriber_count)} subscribers
                      </p>
                    </div>
                    {sub.channel.category && (
                      <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded capitalize">
                        {sub.channel.category}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-gray-500">
                <p>No channels subscribed yet</p>
                <Link href="/channels">
                  <Button variant="primary" size="sm" className="mt-2">
                    <Plus className="w-4 h-4 mr-1" /> Add your first channel
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link href="/channels">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Plus className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Add Channel</p>
                <p className="text-sm text-gray-500">Search and subscribe</p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/feed">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-lg">
                <PlaySquare className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Browse Videos</p>
                <p className="text-sm text-gray-500">View summaries</p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/newsletters">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 bg-purple-100 rounded-lg">
                <Mail className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Create Newsletter</p>
                <p className="text-sm text-gray-500">Generate digest</p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
