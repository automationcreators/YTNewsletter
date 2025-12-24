'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { User, CreditCard, Bell, Shield, LogOut, Crown, Check } from 'lucide-react';

export default function SettingsPage() {
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

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

  const isPremium = user?.subscription_tier === 'premium';

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">Manage your account and preferences</p>
      </div>

      <div className="space-y-6">
        {/* Profile Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-gray-400" />
              <div>
                <CardTitle>Profile</CardTitle>
                <CardDescription>Your account information</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.display_name || 'User'}
                  className="w-16 h-16 rounded-full"
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
                  <span className="text-2xl font-medium text-blue-700">
                    {user?.email?.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
              <div>
                <p className="font-medium text-gray-900">
                  {user?.display_name || 'No display name'}
                </p>
                <p className="text-sm text-gray-500">{user?.email}</p>
                <p className="text-xs text-gray-400 mt-1">
                  Signed in with Google
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Subscription Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <CreditCard className="w-5 h-5 text-gray-400" />
              <div>
                <CardTitle>Subscription</CardTitle>
                <CardDescription>Manage your subscription plan</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg mb-4">
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900 capitalize">
                    {user?.subscription_tier} Plan
                  </p>
                  {isPremium && <Crown className="w-4 h-4 text-yellow-500" />}
                </div>
                <p className="text-sm text-gray-500">
                  {user?.max_channels === -1
                    ? 'Unlimited channels'
                    : `Up to ${user?.max_channels} channels`}
                </p>
              </div>
              {!isPremium && (
                <Button variant="primary">
                  Upgrade to Premium
                </Button>
              )}
            </div>

            {/* Plan Comparison */}
            <div className="grid grid-cols-2 gap-4">
              <div className={`p-4 rounded-lg border-2 ${!isPremium ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                <p className="font-medium text-gray-900">Free</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">$0</p>
                <ul className="mt-4 space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-green-500" />
                    3 channels
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-green-500" />
                    Weekly digests
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-green-500" />
                    AI summaries
                  </li>
                </ul>
              </div>
              <div className={`p-4 rounded-lg border-2 ${isPremium ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                <p className="font-medium text-gray-900">Premium</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">$9/mo</p>
                <ul className="mt-4 space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-green-500" />
                    20 channels
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-green-500" />
                    Daily digests
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-green-500" />
                    Priority processing
                  </li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Notifications Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-gray-400" />
              <div>
                <CardTitle>Notifications</CardTitle>
                <CardDescription>Manage your email preferences</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <label className="flex items-center justify-between cursor-pointer">
                <div>
                  <p className="font-medium text-gray-900">Weekly Digest</p>
                  <p className="text-sm text-gray-500">Receive weekly email summaries</p>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
              </label>
              <label className="flex items-center justify-between cursor-pointer">
                <div>
                  <p className="font-medium text-gray-900">New Video Alerts</p>
                  <p className="text-sm text-gray-500">Get notified when new videos are available</p>
                </div>
                <input
                  type="checkbox"
                  className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
              </label>
            </div>
          </CardContent>
        </Card>

        {/* Security Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Shield className="w-5 h-5 text-gray-400" />
              <div>
                <CardTitle>Security</CardTitle>
                <CardDescription>Account security options</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Button
              variant="danger"
              onClick={logout}
              className="flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
