# Sample service class with metaprogramming
module UserService
  extend self
  
  # Constants
  MAX_LOGIN_ATTEMPTS = 5
  SESSION_TIMEOUT = 30.minutes
  
  # Dynamic method definitions
  %w[create update delete].each do |action|
    define_method "#{action}_user" do |params|
      user = User.new(params) if action == 'create'
      user = User.find(params[:id]) if %w[update delete].include?(action)
      
      case action
      when 'create'
        user.save
      when 'update'
        user.update(params.except(:id))
      when 'delete'
        user.destroy
      end
    end
  end
  
  # Class methods with metaprogramming
  class << self
    attr_accessor :logger
    
    def authenticate(email, password)
      user = User.find_by(email: email)
      return false unless user&.authenticate(password)
      
      log_authentication(user)
      user
    end
    
    def reset_password(email)
      user = User.find_by(email: email)
      return false unless user
      
      token = generate_reset_token
      user.update(reset_token: token, reset_sent_at: Time.current)
      UserMailer.password_reset(user).deliver_now
      true
    end
    
    private
    
    def generate_reset_token
      SecureRandom.urlsafe_base64(32)
    end
    
    def log_authentication(user)
      Rails.logger.info "User #{user.email} authenticated at #{Time.current}"
    end
  end
  
  # Module with mixed concerns
  module Cacheable
    extend ActiveSupport::Concern
    
    included do
      after_save :clear_cache
      after_destroy :clear_cache
    end
    
    class_methods do
      def cached_find(id)
        Rails.cache.fetch("user:#{id}", expires_in: 1.hour) do
          find(id)
        end
      end
    end
    
    private
    
    def clear_cache
      Rails.cache.delete("user:#{id}")
    end
  end
end