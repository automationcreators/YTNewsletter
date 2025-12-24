'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import {
  Mail,
  Plus,
  Trash2,
  ExternalLink,
  Clock,
  CheckCircle,
  AlertCircle,
  Calendar,
  FileText,
  Download,
} from 'lucide-react';
import { formatDate } from '@/lib/utils';
import type { Newsletter } from '@/lib/types';

export default function NewslettersPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [isGenerating, setIsGenerating] = useState(false);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [days, setDays] = useState(7);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Fetch newsletters
  const { data: newsletters, isLoading } = useQuery({
    queryKey: ['newsletters'],
    queryFn: () => api.getNewsletters(1, 20),
    enabled: isAuthenticated,
  });

  // Generate newsletter mutation
  const generateMutation = useMutation({
    mutationFn: (params: { days: number }) => api.createNewsletter(params.days),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['newsletters'] });
      setIsGenerating(false);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteNewsletter(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['newsletters'] });
    },
  });

  // Handle generate
  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      await generateMutation.mutateAsync({ days });
    } catch (error) {
      console.error('Failed to generate newsletter:', error);
      setIsGenerating(false);
    }
  };

  // Handle preview
  const handlePreview = async (newsletterId: string) => {
    try {
      const html = await api.getNewsletterHtml(newsletterId);
      setPreviewHtml(html);
    } catch (error) {
      console.error('Failed to fetch preview:', error);
    }
  };

  // Handle export
  const handleExport = async (newsletter: Newsletter, format: 'html' | 'markdown') => {
    try {
      const result = await api.exportNewsletter(newsletter.id, format);
      const blob = new Blob([result.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `newsletter-${formatDate(newsletter.created_at)}.${format === 'html' ? 'html' : 'md'}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export:', error);
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sent':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'scheduled':
        return <Clock className="w-4 h-4 text-blue-600" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
      default:
        return <FileText className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'sent':
        return 'Sent';
      case 'scheduled':
        return 'Scheduled';
      case 'failed':
        return 'Failed';
      default:
        return 'Draft';
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Newsletters</h1>
          <p className="text-gray-600 mt-1">
            Generate and manage your video digest newsletters
          </p>
        </div>

        {/* Generate Button */}
        <div className="flex items-center gap-3">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
          <Button onClick={handleGenerate} isLoading={isGenerating}>
            <Plus className="w-4 h-4 mr-2" />
            Generate Newsletter
          </Button>
        </div>
      </div>

      {/* Newsletters List */}
      <Card>
        <CardHeader>
          <CardTitle>Your Newsletters ({newsletters?.total || 0})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Loading...</div>
          ) : newsletters?.items?.length > 0 ? (
            <div className="divide-y divide-gray-100">
              {newsletters.items.map((newsletter: Newsletter) => (
                <div
                  key={newsletter.id}
                  className="flex items-center gap-4 p-4 hover:bg-gray-50"
                >
                  {/* Icon */}
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <Mail className="w-6 h-6 text-purple-600" />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900">{newsletter.title}</p>
                    <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(newsletter.created_at)}
                      </span>
                      <span>{newsletter.video_count} videos</span>
                      <span className="flex items-center gap-1">
                        {getStatusIcon(newsletter.status)}
                        {getStatusLabel(newsletter.status)}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePreview(newsletter.id)}
                    >
                      Preview
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport(newsletter, 'html')}
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                    {newsletter.beehiiv_url && (
                      <a
                        href={newsletter.beehiiv_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button variant="outline" size="sm">
                          <ExternalLink className="w-4 h-4" />
                        </Button>
                      </a>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteMutation.mutate(newsletter.id)}
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
              <Mail className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="mb-2">No newsletters yet</p>
              <p className="text-sm text-gray-400">
                Generate your first newsletter to get started
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Preview Modal */}
      {previewHtml && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold">Newsletter Preview</h3>
              <Button variant="ghost" size="sm" onClick={() => setPreviewHtml(null)}>
                Close
              </Button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
              <div
                className="prose max-w-none"
                dangerouslySetInnerHTML={{ __html: previewHtml }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
