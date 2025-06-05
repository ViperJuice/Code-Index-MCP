# Sample Rails controller for testing
class UsersController < ApplicationController
  before_action :set_user, only: [:show, :edit, :update, :destroy]
  before_action :authenticate_user!
  
  # GET /users
  def index
    @users = User.active.includes(:profile)
    @users = @users.where('name ILIKE ?', "%#{params[:search]}%") if params[:search].present?
    @users = @users.page(params[:page])
  end
  
  # GET /users/1
  def show
    @posts = @user.posts.recent.limit(10)
  end
  
  # GET /users/new
  def new
    @user = User.new
  end
  
  # GET /users/1/edit
  def edit
  end
  
  # POST /users
  def create
    @user = User.new(user_params)
    
    if @user.save
      redirect_to @user, notice: 'User was successfully created.'
    else
      render :new
    end
  end
  
  # PATCH/PUT /users/1
  def update
    if @user.update(user_params)
      redirect_to @user, notice: 'User was successfully updated.'
    else
      render :edit
    end
  end
  
  # DELETE /users/1
  def destroy
    @user.destroy
    redirect_to users_url, notice: 'User was successfully deleted.'
  end
  
  private
  
  def set_user
    @user = User.find(params[:id])
  end
  
  def user_params
    params.require(:user).permit(:name, :email, :first_name, :last_name, :active)
  end
  
  protected
  
  def authorize_admin!
    redirect_to root_path unless current_user.admin?
  end
end