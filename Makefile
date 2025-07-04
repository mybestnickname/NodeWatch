restart:
	docker build --tag nodewatch .
	docker stop nodewatch-container || true
	docker rm nodewatch-container || true
	docker run -d -p 8000:8000 --name nodewatch-container nodewatch