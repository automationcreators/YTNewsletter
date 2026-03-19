'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { PlaySquare, Clock, Eye, CheckCircle, Loader2, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { formatRelativeDate, formatDuration, formatNumber, getYouTubeVideoUrl } from '@/lib/utils';
import type { VideoFeedItem } from '@/lib/types';

export default function FeedPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [days, setDays] = useState(7);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  const { data: feed, isLoading, isFetching } = useQuery({
    queryKey: ['video-feed', days, page],
    queryFn: () => api.getVideoFeed(days, page, 20),
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

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Video Feed</h1>
          <p className="text-gray-600 mt-1">
            Recent videos from your subscribed channels
          </p>
        </div>

        {/* Time filter */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Show:</span>
          <select
            value={days}
            onChange={(e) => {
              setDays(Number(e.target.value));
              setPage(1);
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
        </div>
      </div>

      {/* Video Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      ) : feed?.items?.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {feed.items.map((video: VideoFeedItem) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>

          {/* Pagination */}
          <div className="mt-8 flex items-center justify-center gap-4">
            <Button
              variant="outline"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || isFetching}
            >
              Previous
            </Button>
            <span className="text-sm text-gray-600">Page {page}</span>
            <Button
              variant="outline"
              onClick={() => setPage((p) => p + 1)}
              disabled={!feed.has_more || isFetching}
            >
              Next
            </Button>
          </div>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <PlaySquare className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-2">No videos found</p>
            <p className="text-sm text-gray-400 mb-4">
              Subscribe to channels to see their videos here
            </p>
            <Link href="/channels">
              <Button variant="primary">Browse Channels</Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function VideoCard({ video }: { video: VideoFeedItem }) {
  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow">
      {/* Thumbnail */}
      <div className="relative aspect-video bg-gray-100">
        <img
          src={video.thumbnail_url || ''}
          alt={video.title}
          className="w-full h-full object-cover"
        />
        {video.duration_seconds && (
          <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/80 text-white text-xs font-medium rounded">
            {formatDuration(video.duration_seconds)}
          </div>
        )}
        {video.has_summary && (
          <div className="absolute top-2 left-2 px-2 py-1 bg-green-600 text-white text-xs font-medium rounded flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Summary
          </div>
        )}
      </div>

      <CardContent className="p-4">
        {/* Channel info */}
        <div className="flex items-center gap-2 mb-2">
          {video.channel_thumbnail && (
            <img
              src={video.channel_thumbnail}
              alt={video.channel_name}
              className="w-6 h-6 rounded-full"
            />
          )}
          <span className="text-xs text-gray-500 truncate">{video.channel_name}</span>
        </div>

        {/* Title */}
        <h3 className="font-medium text-gray-900 line-clamp-2 mb-2 min-h-[48px]">
          {video.title}
        </h3>

        {/* Meta */}
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Eye className="w-3 h-3" />
            {formatNumber(video.view_count)}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatRelativeDate(video.published_at)}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-4">
          {video.has_summary ? (
            <Link href={`/feed/${video.id}`} className="flex-1">
              <Button variant="primary" size="sm" className="w-full">
                View Summary
              </Button>
            </Link>
          ) : (
            <Button variant="secondary" size="sm" className="flex-1" disabled>
              Generating...
            </Button>
          )}
          <a
            href={getYouTubeVideoUrl(video.youtube_video_id)}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline" size="sm">
              <ExternalLink className="w-4 h-4" />
            </Button>
          </a>
        </div>
      </CardContent>
    </Card>
  );
}
