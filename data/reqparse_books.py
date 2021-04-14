from flask_restful import reqparse


parser = reqparse.RequestParser()
parser.add_argument('title', required=True)
parser.add_argument('author', required=True)
parser.add_argument('genre', required=True)
parser.add_argument('img_url', required=True)
parser.add_argument('year_of_publishing', required=True, type=int)
parser.add_argument('description', required=True)
parser.add_argument('preview_url', required=True)
