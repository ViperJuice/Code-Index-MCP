<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Http\Requests\StoreUserRequest;
use App\Http\Requests\UpdateUserRequest;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Http\JsonResponse;
use Illuminate\View\View;

/**
 * Controller for managing users
 */
class UserController extends Controller
{
    /**
     * Create a new controller instance.
     */
    public function __construct()
    {
        $this->middleware('auth');
        $this->middleware('admin')->only(['destroy', 'create', 'store']);
    }
    
    /**
     * Display a listing of the users.
     */
    public function index(Request $request): View
    {
        $users = User::query()
            ->when($request->search, function ($query, $search) {
                return $query->where('name', 'like', "%{$search}%")
                    ->orWhere('email', 'like', "%{$search}%");
            })
            ->active()
            ->paginate(15);
            
        return view('users.index', compact('users'));
    }
    
    /**
     * Show the form for creating a new user.
     */
    public function create(): View
    {
        return view('users.create');
    }
    
    /**
     * Store a newly created user in storage.
     */
    public function store(StoreUserRequest $request): JsonResponse
    {
        $user = User::create($request->validated());
        
        return response()->json([
            'message' => 'User created successfully',
            'user' => $user
        ], Response::HTTP_CREATED);
    }
    
    /**
     * Display the specified user.
     */
    public function show(User $user): View
    {
        $user->load(['posts', 'profile']);
        
        return view('users.show', compact('user'));
    }
    
    /**
     * Show the form for editing the specified user.
     */
    public function edit(User $user): View
    {
        $this->authorize('update', $user);
        
        return view('users.edit', compact('user'));
    }
    
    /**
     * Update the specified user in storage.
     */
    public function update(UpdateUserRequest $request, User $user): JsonResponse
    {
        $this->authorize('update', $user);
        
        $user->update($request->validated());
        
        return response()->json([
            'message' => 'User updated successfully',
            'user' => $user
        ]);
    }
    
    /**
     * Remove the specified user from storage.
     */
    public function destroy(User $user): JsonResponse
    {
        $this->authorize('delete', $user);
        
        $user->delete();
        
        return response()->json([
            'message' => 'User deleted successfully'
        ]);
    }
    
    /**
     * Get user statistics.
     */
    public function stats(): JsonResponse
    {
        $stats = [
            'total' => User::count(),
            'active' => User::active()->count(),
            'recent' => User::where('created_at', '>=', now()->subDays(30))->count(),
        ];
        
        return response()->json($stats);
    }
    
    /**
     * Bulk action for users.
     */
    public function bulkAction(Request $request): JsonResponse
    {
        $request->validate([
            'action' => 'required|in:activate,deactivate,delete',
            'user_ids' => 'required|array',
            'user_ids.*' => 'exists:users,id'
        ]);
        
        $users = User::whereIn('id', $request->user_ids);
        
        switch ($request->action) {
            case 'activate':
                $users->update(['status' => User::STATUS_ACTIVE]);
                break;
            case 'deactivate':
                $users->update(['status' => User::STATUS_INACTIVE]);
                break;
            case 'delete':
                $users->delete();
                break;
        }
        
        return response()->json([
            'message' => 'Bulk action completed successfully'
        ]);
    }
    
    /**
     * Private helper method to get filtered users.
     */
    private function getFilteredUsers(Request $request)
    {
        return User::query()
            ->when($request->status, function ($query, $status) {
                return $query->where('status', $status);
            })
            ->when($request->role, function ($query, $role) {
                return $query->where('role', $role);
            });
    }
    
    /**
     * Protected method to check user permissions.
     */
    protected function checkPermissions(User $user): bool
    {
        return auth()->user()->canEdit($user);
    }
}