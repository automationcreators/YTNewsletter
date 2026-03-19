'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import {
  ArrowLeft,
  Clock,
  Eye,
  Calendar,
  ExternalLink,
  Quote,
  Lightbulb,
  BookOpen,
  Hash,
} from 'lucide-react';
import Link from 'next/link';
import { formatRelativeDate, formatDuration, formatNumber, getYouTubeVideoUrl } from '@/lib/utils';

export default function VideoDetailPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const videoId = params.id as string;

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Fetch video details
  const { data: video, isLoading: videoLoading } = useQuery({
    queryKey: ['video', videoId],
    queryFn: () => api.getStoredVideo(videoId),
    enabled: isAuthenticated && !!videoId,
  });

  // Fetch video summary
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['video-summary', videoId],
    queryFn: () => api.getVideoSummary(videoId),
    enabled: isAuthenticated && !!videoId,
  });

  if (authLoading || videoLoading) {
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
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      {/* Back Button */}
      <Link href="/feed" className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to Feed
      </Link>

      {video && (
        <>
          {/* Video Header */}
          <div className="mb-8">
            {/* Thumbnail */}
            <div className="relative aspect-video bg-gray-100 rounded-xl overflow-hidden mb-6">
              <img
                src={video.thumbnail_url || ''}
                alt={video.title}
                className="w-full h-full object-cover"
              />
              {video.duration_seconds && (
                <div className="absolute bottom-4 right-4 px-3 py-1.5 bg-black/80 text-white text-sm font-medium rounded">
                  {formatDuration(video.duration_seconds)}
                </div>
              )}
            </div>

            {/* Title and Meta */}
            <h1 className="text-2xl font-bold text-gray-900 mb-4">{video.title}</h1>

            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 mb-4">
              <span className="flex items-center gap-1">
                <Eye className="w-4 h-4" />
                {formatNumber(video.view_count)} views
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {formatRelativeDate(video.published_at)}
              </span>
              {video.duration_seconds && (
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {formatDuration(video.duration_seconds)}
                </span>
              )}
            </div>

            <a
              href={getYouTubeVideoUrl(video.youtube_video_id)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" className="flex items-center gap-2">
                <ExternalLink className="w-4 h-4" />
                Watch on YouTube
              </Button>
            </a>
          </div>

          {/* Summary Content */}
          {summaryLoading ? (
            <Card>
              <CardContent className="py-12 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4" />
                <p className="text-gray-500">Loading summary...</p>
              </CardContent>
            </Card>
          ) : summary ? (
            <div className="space-y-6">
              {/* Main Summary */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-5 h-5 text-blue-600" />
                    <CardTitle>Summary</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {summary.summary_text}
                  </p>
                </CardContent>
              </Card>

              {/* Key Insights */}
              {summary.key_insights && summary.key_insights.length > 0 && (
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Lightbulb className="w-5 h-5 text-yellow-500" />
                      <CardTitle>Key Insights</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-3">
                      {summary.key_insights.map((insight: string, index: number) => (
                        <li key={index} className="flex items-start gap-3">
                          <span className="flex-shrink-0 w-6 h-6 bg-yellow-100 text-yellow-700 rounded-full flex items-center justify-center text-sm font-medium">
                            {index + 1}
                          </span>
                          <span className="text-gray-700">{insight}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Notable Quotes */}
              {summary.notable_quotes && summary.notable_quotes.length > 0 && (
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Quote className="w-5 h-5 text-purple-600" />
                      <CardTitle>Notable Quotes</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {summary.notable_quotes.map((quote: string, index: number) => (
                        <blockquote
                          key={index}
                          className="border-l-4 border-purple-200 pl-4 py-2 italic text-gray-600"
                        >
                          &ldquo;{quote}&rdquo;
                        </blockquote>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Topics/Tags */}
              {summary.topics && summary.topics.length > 0 && (
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Hash className="w-5 h-5 text-gray-500" />
                      <CardTitle>Topics</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {summary.topics.map((topic: string, index: number) => (
                        <span
                          key={index}
                          className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                        >
                          {topic}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-gray-500 mb-4">No summary available yet</p>
                <Button
                  variant="primary"
                  onClick={() => api.generateSummary(videoId)}
                >
                  Generate Summary
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
