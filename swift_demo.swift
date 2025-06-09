import Foundation
import UIKit
import SwiftUI

// Property wrapper example
@propertyWrapper
struct UserDefault<T> {
    let key: String
    let defaultValue: T
    
    var wrappedValue: T {
        get {
            UserDefaults.standard.object(forKey: key) as? T ?? defaultValue
        }
        set {
            UserDefaults.standard.set(newValue, forKey: key)
        }
    }
}

// Result builder example
@resultBuilder
struct HTMLBuilder {
    static func buildBlock(_ components: String...) -> String {
        components.joined(separator: "\n")
    }
    
    static func buildOptional(_ component: String?) -> String {
        component ?? ""
    }
}

// Protocol definition
protocol Drawable {
    func draw()
    var area: Double { get }
}

// Actor for concurrency
actor DatabaseManager {
    private var connections: [String: Database] = [:]
    
    func getConnection(for id: String) async -> Database? {
        return connections[id]
    }
    
    func addConnection(_ db: Database, for id: String) async {
        connections[id] = db
    }
}

// Generic struct with protocol conformance
struct Circle: Drawable, Equatable {
    let radius: Double
    
    var area: Double {
        Double.pi * radius * radius
    }
    
    func draw() {
        print("Drawing circle with radius \(radius)")
    }
}

// Extension with conditional conformance
extension Circle: Codable where Self: Codable {
    // Synthesized conformance
}

// Class with Objective-C interoperability
@objc class SwiftViewController: UIViewController {
    @IBOutlet weak var titleLabel: UILabel!
    @UserDefault(key: "username", defaultValue: "Anonymous")
    var username: String
    
    @IBAction func loginTapped(_ sender: UIButton) {
        authenticate()
    }
    
    @objc func authenticate() {
        // Authentication logic
        performSelector(inBackground: #selector(fetchUserData), with: nil)
    }
    
    @objc func fetchUserData() {
        // Background data fetching
    }
}

// SwiftUI view with property wrappers and result builders
struct ContentView: View {
    @State private var count = 0
    @ObservedObject var dataModel: DataModel
    
    var body: some View {
        VStack {
            Text("Count: \(count)")
            Button("Increment") {
                count += 1
            }
        }
    }
}

// Observable object
class DataModel: ObservableObject {
    @Published var items: [String] = []
    
    func addItem(_ item: String) {
        items.append(item)
    }
}

// Function using result builder
@HTMLBuilder
func buildHTML() -> String {
    "<html>"
    "<body>"
    "<h1>Hello, World!</h1>"
    "</body>"
    "</html>"
}

// Generic function with constraints
func findCommonElements<T: Equatable>(in arrays: [T]...) -> [T] {
    guard let first = arrays.first else { return [] }
    return first.filter { element in
        arrays.allSatisfy { $0.contains(element) }
    }
}

// Protocol with associated types
protocol Container {
    associatedtype Item
    var items: [Item] { get set }
    
    mutating func append(_ item: Item)
    subscript(i: Int) -> Item { get }
}

// Implementation with generic constraints
struct Stack<Element>: Container {
    var items: [Element] = []
    
    mutating func append(_ item: Element) {
        items.append(item)
    }
    
    subscript(i: Int) -> Element {
        return items[i]
    }
}

// Error handling with custom errors
enum NetworkError: Error, LocalizedError {
    case invalidURL
    case noData
    case decodingFailed
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL provided"
        case .noData:
            return "No data received"
        case .decodingFailed:
            return "Failed to decode response"
        }
    }
}

// Async/await function
func fetchData(from url: URL) async throws -> Data {
    let (data, _) = try await URLSession.shared.data(from: url)
    return data
}

// Main app entry point
@main
struct SwiftDemoApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView(dataModel: DataModel())
        }
    }
}