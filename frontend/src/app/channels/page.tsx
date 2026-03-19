'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Search, Plus, Trash2, ExternalLink, AlertCircle } from 'lucide-react';
import { formatNumber } from '@/lib/utils';
import type { ChannelSearchResult, Subscription } from '@/lib/types';

export default function ChannelsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ChannelSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Fetch subscriptions
  const { data: subscriptions, isLoading: subsLoading } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: () => api.getSubscriptions(),
    enabled: isAuthenticated,
  });

  // Fetch subscription limit
  const { data: limit } = useQuery({
    queryKey: ['subscription-limit'],
    queryFn: () => api.getSubscriptionLimit(),
    enabled: isAuthenticated,
  });

  // Subscribe mutation
  const subscribeMutation = useMutation({
    mutationFn: (channelId: string) => api.subscribe(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      queryClient.invalidateQueries({ queryKey: ['subscription-limit'] });
    },
  });

  // Unsubscribe mutation
  const unsubscribeMutation = useMutation({
    mutationFn: (channelId: string) => api.unsubscribe(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      queryClient.invalidateQueries({ queryKey: ['subscription-limit'] });
    },
  });

  // Search for channels
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setSearchError(null);
    setSearchResults([]);

    try {
      const results = await api.searchChannels(searchQuery, 10);
      setSearchResults(results);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setSearchError(err.response?.data?.detail || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  // Check if channel is already subscribed
  const isSubscribed = (youtubeChannelId: string) => {
    return subscriptions?.some(
      (sub: Subscription) => sub.channel.youtube_channel_id === youtubeChannelId
    );
  };

  // Handle subscribe
  const handleSubscribe = async (result: ChannelSearchResult) => {
    if (!limit?.can_subscribe) {
      alert(`You've reached your limit of ${limit?.max_channels} channels. Upgrade to premium for more!`);
      return;
    }

    try {
      // First resolve the channel to get/create it in our DB
      const channel = await api.resolveChannel(result.youtube_channel_id);
      // Then subscribe
      await subscribeMutation.mutateAsync(channel.id);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      alert(err.response?.data?.detail || 'Failed to subscribe');
    }
  };

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
  const maxChannels = limit?.max_channels || 3;
  const canSubscribe = limit?.can_subscribe ?? true;

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Channels</h1>
        <p className="text-gray-600 mt-1">
          Search for YouTube channels and manage your subscriptions.
        </p>
      </div>

      {/* Usage Banner */}
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-blue-900">
            Subscription Limit: {channelCount} / {maxChannels} channels
          </p>
          <p className="text-xs text-blue-700 mt-0.5">
            {canSubscribe
              ? `You can add ${maxChannels - channelCount} more channels`
              : 'Upgrade to premium for more channels'}
          </p>
        </div>
        {!canSubscribe && (
          <Button variant="primary" size="sm">
            Upgrade Plan
          </Button>
        )}
      </div>

      {/* Search Section */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Search Channels</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <div className="flex-1">
              <Input
                placeholder="Search by channel name, URL, or @handle..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <Button onClick={handleSearch} isLoading={isSearching}>
              <Search className="w-4 h-4 mr-2" />
              Search
            </Button>
          </div>

          {/* Search Error */}
          {searchError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
              <AlertCircle className="w-4 h-4" />
              <p className="text-sm">{searchError}</p>
            </div>
          )}

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="mt-6 space-y-3">
              <p className="text-sm text-gray-500">
                Found {searchResults.length} channels
              </p>
              {searchResults.map((result) => (
                <div
                  key={result.youtube_channel_id}
                  className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg"
                >
                  <img
                    src={result.thumbnail_url}
                    alt={result.title}
                    className="w-12 h-12 rounded-full"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{result.title}</p>
                    <p className="text-sm text-gray-500 truncate">{result.description}</p>
                    <p className="text-xs text-gray-400">
                      {formatNumber(result.subscriber_count)} subscribers
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={`https://youtube.com/channel/${result.youtube_channel_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-gray-400 hover:text-gray-600"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    {isSubscribed(result.youtube_channel_id) ? (
                      <Button variant="secondary" size="sm" disabled>
                        Subscribed
                      </Button>
                    ) : (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleSubscribe(result)}
                        isLoading={subscribeMutation.isPending}
                        disabled={!canSubscribe}
                      >
                        <Plus className="w-4 h-4 mr-1" />
                        Subscribe
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Subscribed Channels */}
      <Card>
        <CardHeader>
          <CardTitle>Your Subscriptions ({channelCount})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {subsLoading ? (
            <div className="p-6 text-center text-gray-500">Loading...</div>
          ) : subscriptions?.length > 0 ? (
            <div className="divide-y divide-gray-100">
              {subscriptions.map((sub: Subscription) => (
                <div
                  key={sub.id}
                  className="flex items-center gap-4 p-4 hover:bg-gray-50"
                >
                  <img
                    src={sub.channel.thumbnail_url || ''}
                    alt={sub.channel.name}
                    className="w-12 h-12 rounded-full"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {sub.channel.name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {formatNumber(sub.channel.subscriber_count)} subscribers
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      {sub.channel.category && (
                        <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded capitalize">
                          {sub.channel.category}
                        </span>
                      )}
                      {sub.channel.format_type && (
                        <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-600 rounded capitalize">
                          {sub.channel.format_type}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={`https://youtube.com/channel/${sub.channel.youtube_channel_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-gray-400 hover:text-gray-600"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => unsubscribeMutation.mutate(sub.channel_id)}
                      isLoading={unsubscribeMutation.isPending}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              <p className="mb-2">No channels subscribed yet</p>
              <p className="text-sm">Search for channels above to get started!</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
