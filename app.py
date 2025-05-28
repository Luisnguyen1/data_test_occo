from flask import Flask, render_template, jsonify, request
import requests
from modules.account import (
    create_account, save_to_sheet, get_accounts_from_sheet, get_accounts_with_created_status,
    get_token_for_account, generate_random_user_info, update_user_info_api,
    save_user_info_to_sheet, get_user_info_data_from_sheet, generate_smart_user_info,
    update_existing_user_info_row, get_accounts_need_update, process_selective_update
)
from modules.news import (
    upload_files_to_api, create_news_post, create_blog_post, save_news_to_sheet, save_blog_to_sheet,
    get_news_from_sheet, get_blog_from_sheet, process_news_from_sheet, process_blog_from_sheet,
    update_news_status_in_sheet, update_blog_status_in_sheet
)

app = Flask(__name__)

# API endpoints for login
LOGIN_API_URL = 'http://103.147.186.168:8006/api/v1/auth/user/login/'

@app.route('/')
def index():
    """Main page showing accounts and create button"""
    accounts = get_accounts_from_sheet()
    return render_template('index.html', accounts=accounts)

# ========== ACCOUNT ROUTES ==========

@app.route('/create_account', methods=['POST'])
def create_account_route():
    """Create a new account and save to sheet"""
    # Create account via API
    account_data = create_account()
    
    # Save to Google Sheets
    success, message = save_to_sheet(account_data)
    
    return jsonify({
        "success": success,
        "message": message,
        "account_data": account_data
    })

@app.route('/create_multiple_accounts', methods=['POST'])
def create_multiple_accounts_route():
    """Create multiple accounts at once"""
    try:
        data = request.get_json()
        count = int(data.get('count', 1))
        
        # Limit to maximum 10 accounts at once
        if count > 10:
            count = 10
        elif count < 1:
            count = 1
            
        results = []
        success_count = 0
        
        for i in range(count):
            # Create account
            account_data = create_account()
            
            # Save to sheet
            success, message = save_to_sheet(account_data)
            
            results.append({
                "account_data": account_data,
                "saved": success,
                "message": message
            })
            
            if success:
                success_count += 1
                
        return jsonify({
            "success": True,
            "message": f"Created {success_count}/{count} accounts successfully",
            "results": results,
            "total_created": count,
            "total_saved": success_count
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating multiple accounts: {str(e)}"
        })

@app.route('/accounts')
def get_accounts():
    """Get all accounts as JSON"""
    accounts = get_accounts_from_sheet()
    return jsonify(accounts)

@app.route('/api/accounts')
def api_get_accounts():
    """API to get all accounts from sheet"""
    accounts = get_accounts_from_sheet()
    return jsonify(accounts)

@app.route('/created_accounts')
def get_created_accounts():
    """Get accounts with created status"""
    accounts = get_accounts_with_created_status()
    return jsonify(accounts)

@app.route('/api/created_accounts')
def get_created_accounts_api():
    """API to get accounts with created status"""
    accounts = get_accounts_with_created_status()
    return jsonify(accounts)

@app.route('/update_user_info/<account_id>', methods=['POST'])
def update_user_info_route(account_id):
    """Update user info for a specific account"""
    try:
        # Get user info data from request or generate random
        data = request.get_json() or {}
        
        # Generate random user info or use provided data
        user_info = generate_random_user_info()
        
        # Override with provided data if any
        for key in user_info.keys():
            if key in data and data[key]:
                user_info[key] = data[key]
        
        # Get avatar URL from data if provided
        avatar_url = data.get('avatar', '')
        
        # Get token (placeholder - in real app you'd need to login first)
        token = get_token_for_account(account_id)
        
        # Update user info via API
        update_result = update_user_info_api(account_id, token, user_info, avatar_url)
        
        # Update existing row instead of creating new one
        success, message = update_existing_user_info_row(account_id, user_info, update_result, avatar_url)
        
        return jsonify({
            "success": success,
            "message": message,
            "user_info": user_info,
            "update_result": update_result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error updating user info: {str(e)}"
        })

@app.route('/update_multiple_user_info', methods=['POST'])
def update_multiple_user_info_route():
    """Update user info for multiple accounts"""
    try:
        # Get created accounts from sheet
        created_accounts = get_accounts_with_created_status()
        
        if not created_accounts:
            return jsonify({
                "success": False,
                "message": "No created accounts found"
            })
        
        results = []
        success_count = 0
        
        for account in created_accounts:
            account_id = account['account_id']
            
            # Generate random user info
            user_info = generate_random_user_info()
            
            # Get token (placeholder)
            token = get_token_for_account(account_id)
            
            # Update user info via API
            update_result = update_user_info_api(account_id, token, user_info)
            
            # Save to sheet
            success, message = save_user_info_to_sheet(account_id, user_info, update_result)
            
            results.append({
                "account_id": account_id,
                "phone_number": account['phone_number'],
                "user_info": user_info,
                "update_result": update_result,
                "saved": success,
                "message": message
            })
            
            if success:
                success_count += 1
                
        return jsonify({
            "success": True,
            "message": f"Updated {success_count}/{len(created_accounts)} user info successfully",
            "results": results,
            "total_accounts": len(created_accounts),
            "total_updated": success_count
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error updating multiple user info: {str(e)}"
        })

@app.route('/update_user_info_page')
def update_user_info_page():
    """Page for updating user info with smart logic"""
    return render_template('update_user_info.html')

@app.route('/api/user_info_data')
def get_user_info_data():
    """API to get existing user info data from sheets"""
    user_info_data = get_user_info_data_from_sheet()
    return jsonify(user_info_data)

@app.route('/api/smart_update_user_info/<account_id>', methods=['POST'])
def smart_update_user_info_route(account_id):
    """Smart update user info for a specific account - only fill empty fields"""
    try:
        # Get existing user info from sheet
        existing_user_info_list = get_user_info_data_from_sheet()
        existing_user_info = None
        
        # Find existing data for this account
        for info in existing_user_info_list:
            if info['account_id'] == account_id:
                existing_user_info = info
                break
        
        # Get token
        token = get_token_for_account(account_id)
        
        # Get avatar URL from existing data
        avatar_url = existing_user_info.get('avatar', '') if existing_user_info else ''
        
        # Smart update (keep existing data, fill empty fields)
        user_info = generate_smart_user_info(existing_user_info)
        update_result = update_user_info_api(account_id, token, user_info, avatar_url)
        
        # Update existing row instead of creating new one
        success, message = update_existing_user_info_row(account_id, user_info, update_result, avatar_url)
        
        return jsonify({
            "success": success,
            "message": message,
            "user_info": user_info,
            "update_result": update_result,
            "had_existing_data": existing_user_info is not None
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error in smart update: {str(e)}"
        })

@app.route('/api/smart_update_multiple_user_info', methods=['POST'])
def smart_update_multiple_user_info_route():
    """Smart update user info for multiple accounts"""
    try:
        # Get created accounts and existing user info
        created_accounts = get_accounts_with_created_status()
        existing_user_info_list = get_user_info_data_from_sheet()
        
        if not created_accounts:
            return jsonify({
                "success": False,
                "message": "No created accounts found"
            })
        
        results = []
        success_count = 0
        updated_count = 0
        skipped_count = 0
        
        for account in created_accounts:
            account_id = account['account_id']
            
            # Find existing data for this account
            existing_user_info = None
            for info in existing_user_info_list:
                if info['account_id'] == account_id:
                    existing_user_info = info
                    break
            
            # Check if we need to update (has missing fields)
            needs_update = False
            if existing_user_info is None:
                needs_update = True
            else:
                # Check for empty fields
                required_fields = ['full_name', 'bio', 'email', 'date_of_birth', 'gender', 'height', 'weight', 'country', 'province', 'lat', 'lng']
                for field in required_fields:
                    if field not in existing_user_info or not existing_user_info[field] or existing_user_info[field].strip() == '':
                        needs_update = True
                        break
            
            if not needs_update:
                skipped_count += 1
                results.append({
                    "account_id": account_id,
                    "phone_number": account['phone_number'],
                    "status": "skipped",
                    "message": "All fields already have data"
                })
                continue
            
            # Get token
            token = get_token_for_account(account_id)
            
            # Get avatar URL from existing data
            avatar_url = existing_user_info.get('avatar', '') if existing_user_info else ''
            
            # Smart update
            user_info = generate_smart_user_info(existing_user_info)
            update_result = update_user_info_api(account_id, token, user_info, avatar_url)
            
            # Update existing row instead of creating new one
            success, message = update_existing_user_info_row(account_id, user_info, update_result, avatar_url)
            
            results.append({
                "account_id": account_id,
                "phone_number": account['phone_number'],
                "user_info": user_info,
                "update_result": update_result,
                "saved": success,
                "message": message,
                "had_existing_data": existing_user_info is not None
            })
            
            if success:
                success_count += 1
            updated_count += 1
                
        return jsonify({
            "success": True,
            "message": f"Processed {len(created_accounts)} accounts: {updated_count} updated, {skipped_count} skipped, {success_count} successful",
            "results": results,
            "total_accounts": len(created_accounts),
            "total_updated": updated_count,
            "total_skipped": skipped_count,
            "total_successful": success_count
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error in smart update multiple: {str(e)}"
        })

@app.route('/api/selective_update_user_info', methods=['POST'])
def selective_update_user_info_route():
    """Update user info only for accounts with Tình trạng = 'not_update'"""
    try:
        result = process_selective_update()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error in selective update: {str(e)}",
            "results": [],
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0
        })

@app.route('/api/accounts_need_update')
def get_accounts_need_update_api():
    """API to get accounts that need update (Tình trạng = 'not_update')"""
    try:
        accounts = get_accounts_need_update()
        return jsonify({
            "success": True,
            "accounts": accounts,
            "total_count": len(accounts)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error getting accounts: {str(e)}",
            "accounts": [],
            "total_count": 0
        })

@app.route('/api/get_token/<account_id>', methods=['GET'])
def api_get_token(account_id):
    """API to get authentication token for an account"""
    try:
        token = get_token_for_account(account_id)
        
        if token:
            return jsonify({
                'success': True,
                'token': token,
                'account_id': account_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not get token for account',
                'account_id': account_id
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'account_id': account_id
        }), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for login"""
    try:
        data = request.json
        phone_number = data.get('phone_number', '')
        password = data.get('password', '')
        
        if not phone_number or not password:
            return jsonify({
                'success': False,
                'message': 'Phone number and password are required'
            }), 400
        
        # Login to get token
        login_data = {
            'phone_number': phone_number,
            'password': password,
            'platform': 'ANDROID',
            'device_token': 'fGyH6vLm90c:APA91bH_F_lpVy9yWx3H8s9DzRmH7Vq6PwF5Vu1ZkZo9KcY8eQhGmX1V4Ue4VdX1T2Ue3WbAfMrS8rQyMgV_C7R9bVhWmWzH1VvF6N2Tzx',
            'device_name': 'ANDROID REDMI NOTE12'
        }
        
        headers = {
            'Host': 'localhost:8006',
            'X-Real-IP': '127.0.0.1', 
            'X-Forwarded-For': '127.0.0.1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(LOGIN_API_URL, json=login_data, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            # Extract token from response
            if 'access_token' in response_data:
                token = response_data['access_token']
            elif 'data' in response_data and 'access_token' in response_data['data']:
                token = response_data['data']['access_token']
            elif 'token' in response_data:
                token = response_data['token']
            else:
                return jsonify({
                    'success': False,
                    'message': f'No token found in response: {response_data}'
                }), 400
                
            return jsonify({
                'success': True,
                'token': token,
                'message': 'Login successful'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Login failed: {response.status_code} - {response.text}'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error during login: {str(e)}'
        }), 500

# ========== NEWS ROUTES ==========

@app.route('/news_page')
def news_page():
    """Page for creating and viewing news posts"""
    return render_template('news.html')

@app.route('/blog_page')
def blog_page():
    """Page for creating and viewing blog posts"""
    return render_template('blog.html')

@app.route('/api/news', methods=['GET'])
def api_get_news():
    """API to get all news from sheet"""
    news = get_news_from_sheet()
    return jsonify(news)

@app.route('/api/blog', methods=['GET'])
def api_get_blog():
    """API to get all blog from sheet"""
    blog = get_blog_from_sheet()
    return jsonify(blog)

@app.route('/api/create_news', methods=['POST'])
def api_create_news():
    """API to create news post"""
    try:
        data = request.json
        user_id = data.get('user_id', '')
        title = data.get('title', '')
        content = data.get('content', '')
        privacy = data.get('privacy', 'PUBLIC')
        files = data.get('files', '')  # Comma-separated URLs
        token = data.get('token', '')
        
        if not title or not content:
            return jsonify({
                'success': False,
                'message': 'Title and content are required'
            }), 400
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Token is required'
            }), 400
        
        # Process file URLs
        file_urls = []
        if files:
            file_urls = [url.strip() for url in files.split(',') if url.strip()]
        
        # Upload files and get IDs
        file_ids = upload_files_to_api(file_urls, token)
        
        # Create news post
        result = create_news_post(title, content, privacy, file_ids, token)
        
        # Save to sheet
        save_success, save_message = save_news_to_sheet(user_id, title, content, privacy, result)
        
        return jsonify({
            'success': result['success'],
            'news_id': result.get('news_id', ''),
            'message': 'News post created successfully' if result['success'] else 'Failed to create news post',
            'file_ids': file_ids,
            'save_to_sheet': save_success,
            'details': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/create_blog', methods=['POST'])
def api_create_blog():
    """API to create blog post"""
    try:
        data = request.json
        user_id = data.get('user_id', '')
        title = data.get('title', '')
        content = data.get('content', '')
        privacy = data.get('privacy', 'PUBLIC')
        files = data.get('files', '')  # Comma-separated URLs
        token = data.get('token', '')
        
        if not title or not content:
            return jsonify({
                'success': False,
                'message': 'Title and content are required'
            }), 400
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Token is required'
            }), 400
        
        # Process file URLs
        file_urls = []
        if files:
            file_urls = [url.strip() for url in files.split(',') if url.strip()]
        
        # Upload files and get IDs
        file_ids = upload_files_to_api(file_urls, token)
        
        # Create blog post
        result = create_blog_post(title, content, privacy, file_ids, token)
        
        # Save to sheet
        save_success, save_message = save_blog_to_sheet(user_id, title, content, privacy, result)
        
        return jsonify({
            'success': result['success'],
            'blog_id': result.get('blog_id', ''),
            'message': 'Blog post created successfully' if result['success'] else 'Failed to create blog post',
            'file_ids': file_ids,
            'save_to_sheet': save_success,
            'details': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/process_news_from_sheet', methods=['POST'])
def api_process_news_from_sheet():
    """API to process news posts from sheet"""
    try:
        data = request.json
        token = data.get('token', '')
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Token is required'
            }), 400
        
        # Process news from sheet
        result = process_news_from_sheet(token)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/process_blog_from_sheet', methods=['POST'])
def api_process_blog_from_sheet():
    """API to process blog posts from sheet"""
    try:
        data = request.json
        token = data.get('token', '')
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Token is required'
            }), 400
        
        # Process blog from sheet
        result = process_blog_from_sheet(token)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/news_with_accounts', methods=['GET'])
def api_get_news_with_accounts():
    """API to get news data with account information for authentication"""
    try:
        # Get news data
        news = get_news_from_sheet()
        
        # Get all account data to enable login
        accounts = get_accounts_from_sheet()
        
        # Format accounts for easier lookup
        formatted_accounts = []
        for account in accounts:
            if account.get('status') == 'created' and account.get('account_id'):
                formatted_accounts.append({
                    'id': account.get('account_id'),
                    'phone_number': account.get('phone_number'),
                    'password': account.get('password')
                })
        
        return jsonify({
            'news': news,
            'accounts': formatted_accounts
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/blog_with_accounts', methods=['GET'])
def api_get_blog_with_accounts():
    """API to get blog data with account information for authentication"""
    try:
        # Get blog data
        blog = get_blog_from_sheet()
        
        # Get all account data to enable login
        accounts = get_accounts_from_sheet()
        
        # Format accounts for easier lookup
        formatted_accounts = []
        for account in accounts:
            if account.get('status') == 'created' and account.get('account_id'):
                formatted_accounts.append({
                    'id': account.get('account_id'),
                    'phone_number': account.get('phone_number'),
                    'password': account.get('password')
                })
        
        return jsonify({
            'blog': blog,
            'accounts': formatted_accounts
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/post_single_news', methods=['POST'])
def api_post_single_news():
    """API to post a single news item from sheet data"""
    try:
        data = request.json
        token = data.get('token', '')
        row_index = data.get('row_index')
        user_id = data.get('user_id', '')
        title = data.get('title', '')
        content = data.get('content', '')
        privacy = data.get('privacy', 'PUBLIC')
        files = data.get('files', '')   # Comma-separated URLs
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Token is required'
            }), 400
            
        if not title or not content:
            return jsonify({
                'success': False,
                'message': 'Title and content are required'
            }), 400
        
        # Process file URLs
        file_urls = []
        if files:
            file_urls = [url.strip() for url in files.split(',') if url.strip()]
        
        # Upload files and get IDs
        file_ids = upload_files_to_api(file_urls, token)
        
        # Create news post
        result = create_news_post(title, content, privacy, file_ids, token)
        
        # If successful, update the Google Sheet
        if result['success']:
            # Add 2 because sheet is 1-indexed and we have a header row
            row_number = row_index + 2
            update_news_status_in_sheet(row_number, 'uploaded', result.get('news_id', ''))
        
        return jsonify({
            'success': result['success'],
            'news_id': result.get('news_id', ''),
            'message': 'News post created successfully' if result['success'] else 'Failed to create news post',
            'details': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/post_single_blog', methods=['POST'])
def api_post_single_blog():
    """API to post a single blog item from sheet data"""
    try:
        data = request.json
        token = data.get('token', '')
        row_index = data.get('row_index')
        user_id = data.get('user_id', '')
        title = data.get('title', '')
        content = data.get('content', '')
        privacy = data.get('privacy', 'PUBLIC')
        files = data.get('files', '')   # Comma-separated URLs
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Token is required'
            }), 400
            
        if not title or not content:
            return jsonify({
                'success': False,
                'message': 'Title and content are required'
            }), 400
        
        # Process file URLs
        file_urls = []
        if files:
            file_urls = [url.strip() for url in files.split(',') if url.strip()]
        
        # Upload files and get IDs
        file_ids = upload_files_to_api(file_urls, token)
        
        # Create blog post
        result = create_blog_post(title, content, privacy, file_ids, token)
        
        # If successful, update the Google Sheet
        if result['success']:
            # Add 2 because sheet is 1-indexed and we have a header row
            row_number = row_index + 2
            update_blog_status_in_sheet(row_number, 'uploaded', result.get('blog_id', ''))
        
        return jsonify({
            'success': result['success'],
            'blog_id': result.get('blog_id', ''),
            'message': 'Blog post created successfully' if result['success'] else 'Failed to create blog post',
            'details': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
